import json
from pathlib import Path

import pytest

from agentic_triage.cli import (
    build_parser,
    report_preflight_failure,
    run_intake,
    run_github,
    settings_from_environment,
    write_run_report,
)
from agentic_triage.models import Stage
from agentic_triage.persistence import SQLiteRepository


def test_offline_intake_creates_persistent_run(tmp_path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "action": "opened",
                "issue": {
                    "number": 8,
                    "title": "Favorite button does not update",
                    "body": "Steps to reproduce",
                    "labels": [{"name": "agent:triage"}],
                },
                "repository": {"full_name": "example/repo"},
            }
        ),
        encoding="utf-8",
    )
    database = tmp_path / "agent.db"
    args = build_parser().parse_args(
        [
            "intake",
            "--event",
            str(event_path),
            "--database",
            str(database),
            "--commit-sha",
            "b" * 40,
            "--no-github",
        ]
    )

    result = run_intake(args)

    assert result == 0
    with SQLiteRepository(database)._connect() as connection:
        row = connection.execute("SELECT run_id FROM runs").fetchone()
    assert row is not None


def test_settings_read_hosted_cost_limit(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MAX_RUN_COST_USD", "0.25")

    settings = settings_from_environment()

    assert settings.limits.max_run_cost_usd == 0.25


def test_sanitized_report_excludes_issue_body_and_logs(tmp_path, run_state) -> None:
    run_state.issue.body = "sensitive issue details"
    run_state.messages.append("raw command log")
    report = tmp_path / "report.json"

    write_run_report(report, run_state, 0.01)

    content = report.read_text(encoding="utf-8")
    assert "sensitive issue details" not in content
    assert "raw command log" not in content


def test_preflight_failure_posts_safe_issue_comment(run_state) -> None:
    class FakeGitHub:
        def __init__(self) -> None:
            self.comments = []

        def add_labels(self, issue_number, labels) -> None:
            pass

        def remove_label(self, issue_number, label) -> None:
            pass

        def upsert_issue_comment(self, issue_number, *, marker, body) -> None:
            self.comments.append(body)

    github = FakeGitHub()
    run_state.transition(Stage.FAILED)

    report_preflight_failure(
        github,
        run_state,
        RuntimeError("<unsafe branch>"),
    )

    assert "failed safely" in github.comments[0]
    assert "&lt;unsafe branch&gt;" in github.comments[0]


def test_decline_records_decision_without_model_call(
    tmp_path,
    monkeypatch,
) -> None:
    class FakeGitHub:
        instances = []

        def __init__(self, **kwargs) -> None:
            self.comments = []
            self.removed = []
            FakeGitHub.instances.append(self)

        def ensure_label(self, *args, **kwargs) -> None:
            pass

        def remove_label(self, issue_number, label) -> None:
            self.removed.append((issue_number, label))

        def upsert_issue_comment(self, issue_number, *, marker, body) -> None:
            self.comments.append(body)

    event_path = tmp_path / "decline.json"
    event_path.write_text(
        json.dumps(
            {
                "action": "labeled",
                "label": {"name": "agent:declined"},
                "issue": {
                    "number": 9,
                    "title": "Risky change",
                    "body": "Do not continue",
                    "labels": [
                        {"name": "agent:needs-information"},
                        {"name": "agent:declined"},
                    ],
                },
                "repository": {"full_name": "example/repo"},
            }
        ),
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    args = build_parser().parse_args(
        [
            "run-github",
            "--event",
            str(event_path),
            "--database",
            str(tmp_path / "agent.db"),
            "--report",
            str(report),
        ]
    )
    monkeypatch.setenv("AGENT_GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_SHA", "c" * 40)
    monkeypatch.setattr("agentic_triage.cli.GitHubClient", FakeGitHub)
    monkeypatch.setattr(
        "agentic_triage.cli.AnthropicGateway",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("model gateway must not be created")
        ),
    )

    result = run_github(args)

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert result == 0
    assert payload["cost_usd"] == 0
    assert payload["models"] == []
    assert "No model call" in FakeGitHub.instances[0].comments[0]


def test_workflow_accepts_all_human_decision_labels() -> None:
    workflow = Path(".github/workflows/agent-intake.yml").read_text(
        encoding="utf-8"
    )

    for label in (
        "agent:triage",
        "agent:retry",
        "agent:investigation-only",
        "agent:approve-draft",
        "agent:declined",
    ):
        assert label in workflow


def test_decline_requires_existing_escalation(tmp_path, monkeypatch) -> None:
    class FakeGitHub:
        def __init__(self, **kwargs) -> None:
            pass

        def ensure_label(self, *args, **kwargs) -> None:
            pass

    event_path = tmp_path / "invalid-decline.json"
    event_path.write_text(
        json.dumps(
            {
                "action": "labeled",
                "label": {"name": "agent:declined"},
                "issue": {
                    "number": 10,
                    "title": "Not escalated",
                    "body": "No prior escalation exists",
                    "labels": [{"name": "agent:declined"}],
                },
                "repository": {"full_name": "example/repo"},
            }
        ),
        encoding="utf-8",
    )
    args = build_parser().parse_args(
        [
            "run-github",
            "--event",
            str(event_path),
            "--database",
            str(tmp_path / "agent.db"),
            "--report",
            str(tmp_path / "report.json"),
        ]
    )
    monkeypatch.setenv("AGENT_GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_SHA", "d" * 40)
    monkeypatch.setattr("agentic_triage.cli.GitHubClient", FakeGitHub)

    with pytest.raises(ValueError, match="existing agent escalation"):
        run_github(args)
