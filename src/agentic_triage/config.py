from __future__ import annotations

from pydantic import BaseModel, Field


class AgentLimits(BaseModel):
    max_code_searches: int = Field(default=8, gt=0)
    max_files_read: int = Field(default=12, gt=0)
    max_repair_attempts: int = Field(default=2, gt=0)
    max_sonnet_escalations: int = Field(default=1, ge=0)
    max_opus_escalations: int = Field(default=0, ge=0)
    max_input_tokens_per_call: int = Field(default=20_000, gt=0)
    max_output_tokens_per_call: int = Field(default=2_000, gt=0)
    max_changed_files: int = Field(default=6, gt=0)
    max_changed_lines: int = Field(default=400, gt=0)
    max_run_cost_usd: float = Field(default=2.0, gt=0)


class AgentSettings(BaseModel):
    limits: AgentLimits = Field(default_factory=AgentLimits)
    high_confidence_threshold: float = Field(default=0.8, ge=0, le=1)
    medium_confidence_threshold: float = Field(default=0.55, ge=0, le=1)
    require_reproduction_for_repair: bool = True
