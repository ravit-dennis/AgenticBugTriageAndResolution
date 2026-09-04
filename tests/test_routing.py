from agentic_triage.config import AgentSettings
from agentic_triage.models import Diagnosis, ModelTier, Risk, Severity
from agentic_triage.routing import select_model


def test_haiku_is_default(run_state) -> None:
    assert select_model(run_state, AgentSettings()) is ModelTier.HAIKU


def test_ambiguous_diagnosis_escalates_once_to_sonnet(run_state) -> None:
    run_state.diagnosis = Diagnosis(
        root_cause="Two plausible request paths",
        severity=Severity.MEDIUM,
        risk=Risk.MEDIUM,
        confidence=0.6,
    )
    settings = AgentSettings()

    assert select_model(run_state, settings) is ModelTier.SONNET
    assert select_model(run_state, settings) is ModelTier.HAIKU
    assert run_state.sonnet_escalations == 1


def test_failed_repair_escalates_once_to_sonnet(run_state) -> None:
    settings = AgentSettings()

    assert (
        select_model(run_state, settings, reasoning_blocked=True)
        is ModelTier.SONNET
    )
    assert (
        select_model(run_state, settings, reasoning_blocked=True)
        is ModelTier.HAIKU
    )
