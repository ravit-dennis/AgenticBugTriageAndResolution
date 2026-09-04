import sys

import pytest

from agentic_triage.tools import RepositoryTools, ToolPolicyError


def test_reads_bounded_lines_and_searches_code(repository_root) -> None:
    tools = RepositoryTools(repository_root)

    assert tools.read_file("src/example.py", 1, 1) == "def calculate_total(items):"
    assert tools.search_code("sum", paths=("src",)) == [
        "src\\example.py:2:return sum(items)"
    ]


def test_rejects_paths_outside_repository(repository_root) -> None:
    tools = RepositoryTools(repository_root)

    with pytest.raises(ToolPolicyError):
        tools.read_file("../secret.txt", 1, 1)


def test_rejects_non_allowlisted_commands(repository_root) -> None:
    tools = RepositoryTools(repository_root)

    with pytest.raises(ToolPolicyError):
        tools.run_command(["curl", "https://example.com"])


def test_runs_allowlisted_command_and_fingerprints_output(repository_root) -> None:
    tools = RepositoryTools(
        repository_root,
        allowed_commands=frozenset({sys.executable.lower()}),
    )

    result = tools.run_command([sys.executable, "-c", "print('ok')"])

    assert result.return_code == 0
    assert result.stdout.strip() == "ok"
    assert len(result.output_fingerprint) == 16


def test_rejects_patch_that_escapes_repository(repository_root) -> None:
    tools = RepositoryTools(repository_root)
    patch = (
        "diff --git a/../secret.txt b/../secret.txt\n"
        "--- a/../secret.txt\n"
        "+++ b/../secret.txt\n"
        "@@ -1 +1 @@\n"
        "-secret\n"
        "+changed\n"
    )

    with pytest.raises(ToolPolicyError, match="escapes repository"):
        tools.apply_patch(patch)


def test_normalizes_fenced_patch_and_final_newline() -> None:
    patch = "```diff\ndiff --git a/file b/file\n--- a/file\n+++ b/file\n```"

    assert RepositoryTools._normalize_patch(patch).endswith("\n")
    assert "```" not in RepositoryTools._normalize_patch(patch)
