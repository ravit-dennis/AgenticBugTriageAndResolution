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
        *,
        investigation_only: bool = False,
        human_approved_draft: bool = False,
    ) -> None:
        self.handlers = handlers
        self.repository = repository
        self.settings = settings or AgentSettings()
        self.investigation_only = investigation_only
        self.human_approved_draft = human_approved_draft

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

            if self.investigation_only:
                state.autonomy_action = AutonomyAction.TRIAGE_ONLY
                return self._escalate(
                    state,
                    "Maintainer requested read-only investigation",
                )

            if self.human_approved_draft:
                if not self._draft_override_is_safe(state):
                    return self._escalate(
                        state,
                        "Hard safety policy prevents an approved draft repair",
                    )
                state.autonomy_action = AutonomyAction.DRAFT_PR
                state.messages.append(
                    "Maintainer approved a bounded draft repair"
                )
                return self._repair_and_validate(state)

            if state.autonomy_action is AutonomyAction.DRAFT_PR:
                return self._escalate(
                    state,
                    "A draft repair requires explicit maintainer approval",
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

    @staticmethod
    def _draft_override_is_safe(state: AgentRunState) -> bool:
        reproduction = state.reproduction
        diagnosis = state.diagnosis
        return bool(
            reproduction
            and reproduction.reproduced
            and diagnosis
            and diagnosis.risk.value != "high"
            and not diagnosis.security_sensitive
            and not diagnosis.migration_required
            and not diagnosis.destructive
        )

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
