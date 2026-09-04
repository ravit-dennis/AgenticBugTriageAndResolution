from __future__ import annotations

from typing import Protocol

from agentic_triage.models import (
    AgentRunState,
    ContextSelection,
    Diagnosis,
    RepairResult,
    ReproductionEvidence,
    ValidationResult,
)


class WorkflowHandlers(Protocol):
    def gather_context(self, state: AgentRunState) -> ContextSelection: ...

    def reproduce(self, state: AgentRunState) -> ReproductionEvidence: ...

    def diagnose(self, state: AgentRunState) -> Diagnosis: ...

    def repair(self, state: AgentRunState) -> RepairResult: ...

    def validate(self, state: AgentRunState) -> ValidationResult: ...

    def publish(self, state: AgentRunState) -> None: ...

    def escalate(self, state: AgentRunState, reason: str) -> None: ...


class RunRepository(Protocol):
    def save_run(self, state: AgentRunState) -> None: ...
