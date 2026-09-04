from agentic_triage.config import AgentSettings
from agentic_triage.models import (
    AutonomyAction,
    Diagnosis,
    RepairResult,
    ReproductionEvidence,
    Risk,
    Severity,
)
from agentic_triage.policy import choose_autonomy_action, patch_requires_approval


def reproduction(reproduced: bool = True) -> ReproductionEvidence:
    return ReproductionEvidence(
        reproduced=reproduced,
        command="pytest tests/test_bug.py",
        expected="one matching article",
        observed="two articles",
        output_fingerprint="abc123",
        confidence=0.95,
    )


def diagnosis(
    *,
    confidence: float = 0.9,
    risk: Risk = Risk.LOW,
    security_sensitive: bool = False,
) -> Diagnosis:
    return Diagnosis(
        root_cause="Filter condition is inverted",
        supporting_files=["backend/controllers/articles.js"],
        severity=Severity.MEDIUM,
        risk=risk,
        confidence=confidence,
        security_sensitive=security_sensitive,
    )


def test_high_confidence_low_risk_bug_is_ready_for_review() -> None:
    action = choose_autonomy_action(
        reproduction(),
        diagnosis(),
        AgentSettings(),
    )

    assert action is AutonomyAction.READY_PR


def test_medium_confidence_bug_opens_draft_pr() -> None:
    action = choose_autonomy_action(
        reproduction(),
        diagnosis(confidence=0.7),
        AgentSettings(),
    )

    assert action is AutonomyAction.DRAFT_PR


def test_unreproduced_or_sensitive_bug_is_triage_only() -> None:
    settings = AgentSettings()

    assert (
        choose_autonomy_action(reproduction(False), diagnosis(), settings)
        is AutonomyAction.TRIAGE_ONLY
    )
    assert (
        choose_autonomy_action(
            reproduction(),
            diagnosis(security_sensitive=True),
            settings,
        )
        is AutonomyAction.TRIAGE_ONLY
    )


def test_large_patch_requires_approval() -> None:
    settings = AgentSettings()

    assert patch_requires_approval(
        RepairResult(
            changed_files=[f"file-{index}.py" for index in range(7)],
            changed_lines=20,
        ),
        settings,
    )
    assert patch_requires_approval(
        RepairResult(changed_files=["one.py"], changed_lines=401),
        settings,
    )
