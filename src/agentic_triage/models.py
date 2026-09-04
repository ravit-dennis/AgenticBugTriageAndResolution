from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Stage(StrEnum):
    INTAKE = "intake"
    CONTEXT = "context"
    REPRODUCE = "reproduce"
    DIAGNOSE = "diagnose"
    ROUTE = "route"
    REPAIR = "repair"
    VALIDATE = "validate"
    PUBLISH = "publish"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Risk(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AutonomyAction(StrEnum):
    READY_PR = "ready_pr"
    DRAFT_PR = "draft_pr"
    TRIAGE_ONLY = "triage_only"


class HumanAction(StrEnum):
    TRIAGE = "agent:triage"
    RETRY = "agent:retry"
    INVESTIGATION_ONLY = "agent:investigation-only"
    APPROVE_DRAFT = "agent:approve-draft"
    DECLINED = "agent:declined"


class ModelTier(StrEnum):
    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


class Issue(BaseModel):
    number: int = Field(gt=0)
    title: str = Field(min_length=1)
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    html_url: str | None = None


class ContextSelection(BaseModel):
    search_queries: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    reasons: dict[str, str] = Field(default_factory=dict)
    prior_memory_ids: list[int] = Field(default_factory=list)


class ReproductionEvidence(BaseModel):
    reproduced: bool
    command: str
    expected: str
    observed: str
    output_fingerprint: str
    confidence: float = Field(ge=0, le=1)


class Diagnosis(BaseModel):
    root_cause: str = Field(min_length=1)
    supporting_files: list[str] = Field(default_factory=list)
    severity: Severity
    risk: Risk
    confidence: float = Field(ge=0, le=1)
    cross_layer: bool = False
    security_sensitive: bool = False
    migration_required: bool = False
    destructive: bool = False


class RepairResult(BaseModel):
    changed_files: list[str] = Field(default_factory=list)
    changed_lines: int = Field(ge=0)
    regression_test: str | None = None
    summary: str = ""


class ValidationResult(BaseModel):
    reproduction_passed: bool
    targeted_tests_passed: bool
    regression_tests_passed: bool
    commands: list[str] = Field(default_factory=list)
    summary: str = ""

    @property
    def passed(self) -> bool:
        return (
            self.reproduction_passed
            and self.targeted_tests_passed
            and self.regression_tests_passed
        )


class UsageRecord(BaseModel):
    stage: Stage
    model: ModelTier
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)
    reason: str


class AgentRunState(BaseModel):
    run_id: str
    issue: Issue
    commit_sha: str
    stage: Stage = Stage.INTAKE
    context: ContextSelection = Field(default_factory=ContextSelection)
    reproduction: ReproductionEvidence | None = None
    diagnosis: Diagnosis | None = None
    autonomy_action: AutonomyAction | None = None
    repair: RepairResult | None = None
    validation: ValidationResult | None = None
    repair_attempts: int = Field(default=0, ge=0)
    sonnet_escalations: int = Field(default=0, ge=0)
    usage: list[UsageRecord] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    human_action: HumanAction = HumanAction.TRIAGE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def transition(self, stage: Stage, message: str | None = None) -> None:
        self.stage = stage
        self.updated_at = utc_now()
        if message:
            self.messages.append(message)
