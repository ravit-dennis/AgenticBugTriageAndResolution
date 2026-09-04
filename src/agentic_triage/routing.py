from __future__ import annotations

from agentic_triage.config import AgentSettings
from agentic_triage.models import AgentRunState, ModelTier


def select_model(
    state: AgentRunState,
    settings: AgentSettings,
    *,
    reasoning_blocked: bool = False,
) -> ModelTier:
    diagnosis = state.diagnosis
    needs_escalation = reasoning_blocked or (
        diagnosis is not None
        and (
            diagnosis.cross_layer
            or diagnosis.confidence < settings.high_confidence_threshold
        )
    )

    if not needs_escalation:
        return ModelTier.HAIKU

    if state.sonnet_escalations < settings.limits.max_sonnet_escalations:
        state.sonnet_escalations += 1
        return ModelTier.SONNET

    return ModelTier.HAIKU
