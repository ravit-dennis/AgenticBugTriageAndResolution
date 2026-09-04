import json

from agentic_triage.cli import (
    build_parser,
    report_preflight_failure,
    run_intake,
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
