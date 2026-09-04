from __future__ import annotations

from agentic_triage.config import AgentSettings
from agentic_triage.models import AgentRunState, AutonomyAction, Stage
from agentic_triage.policy import choose_autonomy_action, patch_requires_approval
from agentic_triage.ports import RunRepository, WorkflowHandlers


class Orchestrator:
    def __init__(
        self,
        handlers: WorkflowHandlers,
        repository: RunRepository,
        settings: AgentSettings | None = None,
    ) -> None:
        self.handlers = handlers
        self.repository = repository
        self.settings = settings or AgentSettings()

    def run(self, state: AgentRunState) -> AgentRunState:
        try:
            self._transition(state, Stage.CONTEXT, "Gathering repository context")
            state.context = self.handlers.gather_context(state)

            self._transition(state, Stage.REPRODUCE, "Reproducing reported behavior")
            state.reproduction = self.handlers.reproduce(state)

            self._transition(state, Stage.DIAGNOSE, "Diagnosing root cause")
            state.diagnosis = self.handlers.diagnose(state)

            self._transition(state, Stage.ROUTE, "Applying autonomy policy")
            state.autonomy_action = choose_autonomy_action(
                state.reproduction,
                state.diagnosis,
                self.settings,
            )

            if state.autonomy_action is AutonomyAction.TRIAGE_ONLY:
                return self._escalate(
                    state,
                    "Risk, confidence, or reproduction policy requires human review",
                )

            return self._repair_and_validate(state)
        except Exception as error:
            state.transition(Stage.FAILED, f"{type(error).__name__}: {error}")
            self.repository.save_run(state)
            raise

    def _repair_and_validate(self, state: AgentRunState) -> AgentRunState:
        while state.repair_attempts < self.settings.limits.max_repair_attempts:
            state.repair_attempts += 1
            self._transition(
                state,
                Stage.REPAIR,
                f"Repair attempt {state.repair_attempts}",
            )
            try:
                state.repair = self.handlers.repair(state)
            except Exception as error:
                state.messages.append(
                    f"Repair attempt {state.repair_attempts} failed: "
                    f"{type(error).__name__}: {error}"
                )
                self.repository.save_run(state)
                continue

            if patch_requires_approval(state.repair, self.settings):
                state.autonomy_action = AutonomyAction.DRAFT_PR
                return self._escalate(
                    state,
                    "Patch exceeds configured file or line limits",
                )

            self._transition(state, Stage.VALIDATE, "Validating repair")
            try:
                state.validation = self.handlers.validate(state)
            except Exception as error:
                state.messages.append(
                    f"Validation attempt {state.repair_attempts} failed: "
                    f"{type(error).__name__}: {error}"
                )
                self.repository.save_run(state)
                continue
            if state.validation.passed:
                self._transition(state, Stage.PUBLISH, "Publishing pull request")
                self.handlers.publish(state)
                self._transition(state, Stage.COMPLETED, "Repair workflow completed")
                return state

        return self._escalate(
            state,
            "Repair attempts exhausted without a validated fix",
        )

    def _escalate(self, state: AgentRunState, reason: str) -> AgentRunState:
        state.transition(Stage.ESCALATED, reason)
        self.handlers.escalate(state, reason)
        self.repository.save_run(state)
        return state

    def _transition(
        self,
        state: AgentRunState,
        stage: Stage,
        message: str,
    ) -> None:
        state.transition(stage, message)
        self.repository.save_run(state)
