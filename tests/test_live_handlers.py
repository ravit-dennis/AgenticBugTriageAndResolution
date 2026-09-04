from agentic_triage.live_handlers import LocalWorkflowHandlers
import pytest


def test_normalizes_powershell_target_app_reproduction() -> None:
    command = LocalWorkflowHandlers._normalize_command(
        "Set-Location target-app; npm test -- --run "
        "backend/helper/example.test.js"
    )

    assert command == [
        "npm",
        "--prefix",
        "target-app",
        "test",
        "--",
        "--run",
        "backend/helper/example.test.js",
    ]


def test_extracts_reproduction_command_from_issue() -> None:
    body = (
        "Run `Set-Location target-app; npm test -- --run "
        "backend/helper/bug.test.js`."
    )

    assert (
        LocalWorkflowHandlers._reproduction_command(body)
        == "Set-Location target-app; npm test -- --run "
        "backend/helper/bug.test.js"
    )


def test_extracts_complete_jsx_path_from_issue() -> None:
    body = "Run frontend/src/components/SettingsForm/SettingsForm.test.jsx."

    assert LocalWorkflowHandlers._paths_from_issue(body) == [
        "frontend/src/components/SettingsForm/SettingsForm.test.jsx"
    ]


def test_converts_model_wildcards_to_safe_search_pattern() -> None:
    assert (
        LocalWorkflowHandlers._safe_search_pattern("offset.*limit")
        == "offset.*limit"
    )


def test_maps_regression_test_to_adjacent_source() -> None:
    assert LocalWorkflowHandlers._source_for_test(
        "target-app/frontend/src/components/SettingsForm/SettingsForm.test.jsx"
    ) == "target-app/frontend/src/components/SettingsForm/SettingsForm.jsx"


def test_rejects_npm_reproduction_outside_target_app() -> None:
    with pytest.raises(ValueError, match="target-app"):
        LocalWorkflowHandlers._normalize_command(
            "npm test -- --run tests/test_secrets.js"
        )


def test_rejects_reproduction_path_traversal() -> None:
    with pytest.raises(ValueError, match="unsafe path"):
        LocalWorkflowHandlers._normalize_command(
            "Set-Location target-app; npm test -- --run ../outside.test.js"
        )


def test_rejects_arbitrary_python_reproduction() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        LocalWorkflowHandlers._normalize_command(
            "python -c \"print('unsafe')\" target-app"
        )


def test_rejects_vitest_option_injection() -> None:
    with pytest.raises(ValueError, match="test file paths"):
        LocalWorkflowHandlers._normalize_command(
            "Set-Location target-app; npm test -- --run "
            "--config=../outside.config.js"
        )


@pytest.mark.parametrize(
    "path",
    [
        "target-app/backend/helper/pagination.test.js",
        "target-app/frontend/src/component.spec.jsx",
        "target-app/package.json",
        "target-app/package-lock.json",
        "target-app/vitest.config.js",
    ],
)
def test_rejects_repair_to_tests_or_test_configuration(path) -> None:
    with pytest.raises(ValueError, match="cannot modify"):
        LocalWorkflowHandlers._validate_repair_path(path)


def test_allows_repair_to_target_application_source() -> None:
    LocalWorkflowHandlers._validate_repair_path(
        "target-app/backend/helper/pagination.js"
    )
