import pytest

from agentic_triage.hosted import agent_branch_name, extract_base_branch
from agentic_triage.tools import ToolPolicyError


def test_hosted_run_defaults_to_main() -> None:
    assert extract_base_branch("## Reproduction\nRun the test.") == "main"


def test_hosted_run_accepts_demo_live_branch() -> None:
    body = "Agent base branch: `demo/live-backend-bug`"

    assert extract_base_branch(body) == "demo/live-backend-bug"


def test_agent_branch_name_is_stable_per_issue() -> None:
    assert agent_branch_name(42) == "agent/issue-42"


@pytest.mark.parametrize(
    "branch",
    [
        "feat/untrusted",
        "demo/live-collaborator-branch",
        "../main",
        "-malicious",
        "demo/../../main",
    ],
)
def test_hosted_run_rejects_untrusted_base_branch(branch) -> None:
    with pytest.raises(ToolPolicyError, match="Untrusted"):
        extract_base_branch(f"Agent base branch: `{branch}`")
