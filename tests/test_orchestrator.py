from __future__ import annotations

from dataclasses import dataclass, field

from agentic_triage.config import AgentSettings
from agentic_triage.models import (
    AgentRunState,
    AutonomyAction,
    ContextSelection,
    Diagnosis,
    RepairResult,
    ReproductionEvidence,
    Risk,
    Severity,
    Stage,
    ValidationResult,
)
from agentic_triage.orchestrator import Orchestrator


@dataclass
class InMemoryRepository:
    saved_stages: list[Stage] = field(default_factory=list)

    def save_run(self, state: AgentRunState) -> None:
        self.saved_stages.append(state.stage)


class FakeHandlers:
    def __init__(
        self,
        *,
        reproduced: bool = True,
        risk: Risk = Risk.LOW,
        confidence: float = 0.95,
        validation_results: list[bool] | None = None,
        changed_lines: int = 10,
    ) -> None:
        self.reproduced = reproduced
        self.risk = risk
        self.confidence = confidence
        self.validation_results = validation_results or [True]
        self.changed_lines = changed_lines
        self.published = False
        self.escalations: list[str] = []
        self.validation_calls = 0

    def gather_context(self, state):
        return ContextSelection(files=["backend/controllers/articles.js"])

    def reproduce(self, state):
        return ReproductionEvidence(
            reproduced=self.reproduced,
            command="npm test -- articles",
            expected="test passes",
            observed="test fails",
            output_fingerprint="abc123",
            confidence=0.95,
        )

    def diagnose(self, state):
        return Diagnosis(
            root_cause="Inverted query predicate",
            supporting_files=state.context.files,
            severity=Severity.MEDIUM,
            risk=self.risk,
            confidence=self.confidence,
        )

    def repair(self, state):
        return RepairResult(
            changed_files=["backend/controllers/articles.js"],
            changed_lines=self.changed_lines,
            regression_test="backend/controllers/articles.test.js",
        )

    def validate(self, state):
        result = self.validation_results[self.validation_calls]
        self.validation_calls += 1
        return ValidationResult(
            reproduction_passed=result,
            targeted_tests_passed=result,
            regression_tests_passed=result,
        )

    def publish(self, state):
        self.published = True

    def escalate(self, state, reason):
        self.escalations.append(reason)


def test_successful_low_risk_run_publishes_ready_pr(run_state) -> None:
    handlers = FakeHandlers()
    repository = InMemoryRepository()

    result = Orchestrator(handlers, repository).run(run_state)

    assert result.stage is Stage.COMPLETED
    assert result.autonomy_action is AutonomyAction.READY_PR
    assert result.repair_attempts == 1
    assert handlers.published
    assert Stage.VALIDATE in repository.saved_stages


def test_unreproduced_bug_escalates_without_repair(run_state) -> None:
    handlers = FakeHandlers(reproduced=False)

    result = Orchestrator(handlers, InMemoryRepository()).run(run_state)

    assert result.stage is Stage.ESCALATED
    assert result.autonomy_action is AutonomyAction.TRIAGE_ONLY
    assert result.repair_attempts == 0
    assert len(handlers.escalations) == 1


def test_failed_first_fix_can_succeed_on_second_attempt(run_state) -> None:
    handlers = FakeHandlers(validation_results=[False, True])

    result = Orchestrator(handlers, InMemoryRepository()).run(run_state)

    assert result.stage is Stage.COMPLETED
    assert result.repair_attempts == 2
    assert handlers.validation_calls == 2


def test_large_patch_escalates_before_validation(run_state) -> None:
    handlers = FakeHandlers(changed_lines=401)

    result = Orchestrator(handlers, InMemoryRepository()).run(run_state)

    assert result.stage is Stage.ESCALATED
    assert result.autonomy_action is AutonomyAction.DRAFT_PR
    assert handlers.validation_calls == 0
