from __future__ import annotations

from agentic_triage.config import AgentSettings
from agentic_triage.models import (
    AutonomyAction,
    Diagnosis,
    RepairResult,
    ReproductionEvidence,
    Risk,
)


def choose_autonomy_action(
    reproduction: ReproductionEvidence,
    diagnosis: Diagnosis,
    settings: AgentSettings,
) -> AutonomyAction:
    if settings.require_reproduction_for_repair and not reproduction.reproduced:
        return AutonomyAction.TRIAGE_ONLY

    if (
        diagnosis.security_sensitive
        or diagnosis.migration_required
        or diagnosis.destructive
        or diagnosis.risk is Risk.HIGH
        or diagnosis.confidence < settings.medium_confidence_threshold
    ):
        return AutonomyAction.TRIAGE_ONLY

    if (
        diagnosis.risk is Risk.LOW
        and diagnosis.confidence >= settings.high_confidence_threshold
        and not diagnosis.cross_layer
    ):
        return AutonomyAction.READY_PR

    return AutonomyAction.DRAFT_PR


def patch_requires_approval(
    repair: RepairResult,
    settings: AgentSettings,
) -> bool:
    return (
        len(repair.changed_files) > settings.limits.max_changed_files
        or repair.changed_lines > settings.limits.max_changed_lines
    )
