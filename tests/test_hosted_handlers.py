import subprocess

from agentic_triage.hosted_handlers import GitHubWorkflowHandlers
from agentic_triage.models import (
    AutonomyAction,
    ContextSelection,
    Diagnosis,
    RepairResult,
    ReproductionEvidence,
    Risk,
    Severity,
    Stage,
    ValidationResult,
)
from agentic_triage.tools import RepositoryTools


class FakeGitHub:
    def __init__(self) -> None:
        self.added = []
        self.removed = []
        self.comments = []
        self.pull_requests = []

    def add_labels(self, issue_number, labels) -> None:
        self.added.append((issue_number, labels))

    def remove_label(self, issue_number, label) -> None:
        self.removed.append((issue_number, label))

    def upsert_issue_comment(self, issue_number, *, marker, body) -> None:
        self.comments.append((issue_number, marker, body))

    def find_pull_request(self, *, head, base):
        return None

    def create_pull_request(self, **kwargs):
        self.pull_requests.append(kwargs)
        return {
            "number": 7,
            "html_url": "https://github.test/example/repo/pull/7",
        }


class FakeRepository:
    def __init__(self) -> None:
        self.memories = 0

    def save_run(self, state) -> None:
        pass

    def record_memory(self, state, **kwargs):
        self.memories += 1
        return self.memories


def handler_for_escalation(tmp_path, run_state):
    handler = GitHubWorkflowHandlers.__new__(GitHubWorkflowHandlers)
    handler.github = FakeGitHub()
    handler.repository = FakeRepository()
    handler.root = tmp_path
    handler.head_branch = "agent/issue-42"
    handler.base_branch = "main"
    handler.repository_name = "example/repo"
    run_state.diagnosis = Diagnosis(
        root_cause="Production-only destructive behavior",
        supporting_files=[],
        severity=Severity.HIGH,
        risk=Risk.HIGH,
        confidence=0.4,
        destructive=True,
    )
    run_state.transition(Stage.ESCALATED)
    return handler


def test_escalation_posts_human_decision_without_branch(tmp_path, run_state) -> None:
    handler = handler_for_escalation(tmp_path, run_state)

    handler.escalate(run_state, "Reproduction policy requires review")

    assert (42, ["agent:needs-information"]) in handler.github.added
    body = handler.github.comments[0][2]
    assert "Human decision required" in body
    assert "Production-only destructive behavior" in body
    assert "Potentially destructive" in body
    assert "agent:retry" in body
    assert "agent:investigation-only" in body
    assert "Draft repair approval is unavailable" in body


def test_failure_comment_does_not_publish_raw_logs(tmp_path, run_state) -> None:
    handler = handler_for_escalation(tmp_path, run_state)
    run_state.messages.append("large raw process output")

    handler.report_failure(run_state, RuntimeError("safe failure summary"))

    body = handler.github.comments[0][2]
    assert "safe failure summary" in body
    assert "large raw process output" not in body


def test_failure_comment_reports_already_pushed_branch(tmp_path, run_state) -> None:
    handler = handler_for_escalation(tmp_path, run_state)
    run_state.metadata["publication"] = {
        "status": "branch_pushed",
        "head_branch": "agent/issue-42",
    }

    handler.report_failure(run_state, RuntimeError("comment API failed"))

    assert "agent/issue-42" in handler.github.comments[0][2]


def test_publish_commits_pushes_and_creates_pr(tmp_path, run_state) -> None:
    root = tmp_path / "work"
    remote = tmp_path / "remote.git"
    root.mkdir()
    (root / "target-app").mkdir()
    source = root / "target-app" / "example.js"
    source.write_text("const value = 1;\n", encoding="utf-8")
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote)],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "switch", "-c", "agent/issue-42"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    source.write_text("const value = 2;\n", encoding="utf-8")

    run_state.context = ContextSelection(files=["target-app/example.js"])
    run_state.reproduction = ReproductionEvidence(
        reproduced=True,
        command="npm --prefix target-app test",
        expected="pass",
        observed="failed",
        output_fingerprint="abc",
        confidence=0.99,
    )
    run_state.diagnosis = Diagnosis(
        root_cause="Incorrect value",
        supporting_files=["target-app/example.js"],
        severity=Severity.MEDIUM,
        risk=Risk.LOW,
        confidence=0.99,
    )
    run_state.autonomy_action = AutonomyAction.READY_PR
    run_state.repair = RepairResult(
        changed_files=["target-app/example.js"],
        changed_lines=2,
        summary="Correct the value",
    )
    run_state.validation = ValidationResult(
        reproduction_passed=True,
        targeted_tests_passed=True,
        regression_tests_passed=True,
        commands=["npm --prefix target-app test"],
    )
    repository = FakeRepository()
    github = FakeGitHub()
    handler = GitHubWorkflowHandlers.__new__(GitHubWorkflowHandlers)
    handler.root = root
    handler.tools = RepositoryTools(root, editable_roots=("target-app",))
    handler.repository = repository
    handler.github = github
    handler.github_token = "test-token"
    handler.repository_name = "example/repo"
    handler.base_branch = "main"
    handler.head_branch = "agent/issue-42"
    configured_origin = subprocess.run(
        ["git", "remote", "get-url", "--push", "origin"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    handler.expected_origin_urls = {configured_origin}

    handler.publish(run_state)

    remote_head = subprocess.run(
        [
            "git",
            "ls-remote",
            str(remote),
            "refs/heads/agent/issue-42",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert remote_head
    assert github.pull_requests[0]["base"] == "main"
    assert github.pull_requests[0]["draft"] is False
    assert repository.memories == 1


def test_publish_marks_approved_repair_as_draft(tmp_path, run_state) -> None:
    handler = GitHubWorkflowHandlers.__new__(GitHubWorkflowHandlers)
    handler.github = FakeGitHub()
    handler.repository = FakeRepository()
    handler.root = tmp_path
    handler.head_branch = "agent/issue-42"
    handler.base_branch = "main"
    handler.repository_name = "example/repo"
    handler._commit_repair = lambda state: None
    handler._push_repair = lambda: None
    run_state.autonomy_action = AutonomyAction.DRAFT_PR
    run_state.reproduction = ReproductionEvidence(
        reproduced=True,
        command="npm test -- safe.test.js",
        expected="pass",
        observed="failed",
        output_fingerprint="abc",
        confidence=0.9,
    )
    run_state.diagnosis = Diagnosis(
        root_cause="Safe but uncertain mapping",
        severity=Severity.MEDIUM,
        risk=Risk.MEDIUM,
        confidence=0.8,
    )
    run_state.repair = RepairResult(
        changed_files=["target-app/example.js"],
        changed_lines=2,
    )
    run_state.validation = ValidationResult(
        reproduction_passed=True,
        targeted_tests_passed=True,
        regression_tests_passed=True,
    )

    handler.publish(run_state)

    assert handler.github.pull_requests[0]["draft"] is True
