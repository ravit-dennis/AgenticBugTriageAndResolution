from __future__ import annotations

from pathlib import Path

import pytest

from agentic_triage.models import AgentRunState, Issue


@pytest.fixture
def run_state() -> AgentRunState:
    return AgentRunState(
        run_id="run-123",
        issue=Issue(
            number=42,
            title="Article filter returns the wrong records",
            body="Steps to reproduce...",
            labels=["agent:triage"],
        ),
        commit_sha="a" * 40,
    )


@pytest.fixture
def repository_root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "example.py").write_text(
        "def calculate_total(items):\n    return sum(items)\n",
        encoding="utf-8",
    )
    return tmp_path
