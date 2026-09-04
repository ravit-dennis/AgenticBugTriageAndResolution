import json

from agentic_triage.cli import build_parser, run_intake
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
