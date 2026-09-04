from __future__ import annotations

import re
from pathlib import Path

from agentic_triage.tools import RepositoryTools, ToolPolicyError

TRUSTED_BASE_BRANCHES = frozenset(
    {
        "main",
        "demo/live-backend-bug",
        "demo/live-frontend-bug",
        "demo/replay-backend-bug",
        "demo/replay-frontend-bug",
        "demo/replay-pagination-contract-bug",
    }
)


def extract_base_branch(issue_body: str) -> str:
    match = re.search(
        r"(?im)^\s*Agent base branch:\s*`?([^`\s]+)`?\s*$",
        issue_body,
    )
    branch = match.group(1) if match else "main"
    if (
        branch not in TRUSTED_BASE_BRANCHES
    ):
        raise ToolPolicyError(f"Untrusted agent base branch: {branch}")
    return branch


def agent_branch_name(issue_number: int) -> str:
    if issue_number < 1:
        raise ToolPolicyError("Issue number must be positive")
    return f"agent/issue-{issue_number}"


def prepare_agent_branch(
    repository_root: str | Path,
    *,
    base_branch: str,
    issue_number: int,
) -> str:
    tools = RepositoryTools(repository_root)
    fetch = tools.run_command(
        ["git", "fetch", "--prune", "origin", base_branch],
        timeout_seconds=120,
    )
    if fetch.return_code != 0:
        raise ToolPolicyError(
            f"Unable to fetch trusted base branch {base_branch}: {fetch.stderr}"
        )

    remote_ref = f"origin/{base_branch}"
    verify = tools.run_command(
        ["git", "rev-parse", "--verify", remote_ref],
    )
    if verify.return_code != 0:
        raise ToolPolicyError(f"Base branch does not exist: {base_branch}")

    head_branch = agent_branch_name(issue_number)
    remote_head = f"origin/{head_branch}"
    existing = tools.run_command(
        ["git", "rev-parse", "--verify", remote_head],
    )
    if existing.return_code == 0:
        raise ToolPolicyError(
            f"Existing branch {head_branch} requires human review"
        )

    switch = tools.run_command(
        ["git", "switch", "-C", head_branch, remote_ref],
    )
    if switch.return_code != 0:
        raise ToolPolicyError(
            f"Unable to prepare agent branch {head_branch}: {switch.stderr}"
        )
    return head_branch
