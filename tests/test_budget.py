import pytest

from agentic_triage.budget import BudgetExceededError, BudgetTracker
from agentic_triage.models import ModelTier, Stage, UsageRecord


def usage(cost: float) -> UsageRecord:
    return UsageRecord(
        stage=Stage.DIAGNOSE,
        model=ModelTier.HAIKU,
        input_tokens=100,
        output_tokens=20,
        estimated_cost_usd=cost,
        reason="diagnosis",
    )


def test_budget_tracks_spend_and_remaining() -> None:
    tracker = BudgetTracker(max_cost_usd=1.0)

    tracker.record(usage(0.25))
    tracker.record(usage(0.15))

    assert tracker.spent_usd == pytest.approx(0.4)
    assert tracker.remaining_usd == pytest.approx(0.6)


def test_budget_rejects_record_that_exceeds_limit() -> None:
    tracker = BudgetTracker(max_cost_usd=0.5)
    tracker.record(usage(0.4))

    with pytest.raises(BudgetExceededError):
        tracker.record(usage(0.2))

    assert tracker.spent_usd == pytest.approx(0.4)
