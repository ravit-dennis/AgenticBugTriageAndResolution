from agentic_triage.live_handlers import LocalWorkflowHandlers


def test_normalizes_powershell_target_app_reproduction() -> None:
    command = LocalWorkflowHandlers._normalize_command(
        "Set-Location target-app; npm test -- --run backend/helper/test.js"
    )

    assert command == [
        "npm",
        "--prefix",
        "target-app",
        "test",
        "--",
        "--run",
        "backend/helper/test.js",
    ]


def test_extracts_reproduction_command_from_issue() -> None:
    body = "Run `Set-Location target-app; npm test -- --run bug.test.js`."

    assert (
        LocalWorkflowHandlers._reproduction_command(body)
        == "Set-Location target-app; npm test -- --run bug.test.js"
    )


def test_converts_model_wildcards_to_safe_search_pattern() -> None:
    assert (
        LocalWorkflowHandlers._safe_search_pattern("offset.*limit")
        == "offset.*limit"
    )
