from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, TypeVar

from anthropic import Anthropic
from pydantic import BaseModel

from agentic_triage.budget import BudgetTracker
from agentic_triage.config import AgentSettings
from agentic_triage.models import ModelTier, Stage, UsageRecord

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


@dataclass(frozen=True)
class ModelDefinition:
    model_id: str
    input_cost_per_million: float
    output_cost_per_million: float


MODEL_CATALOG: dict[ModelTier, ModelDefinition] = {
    ModelTier.HAIKU: ModelDefinition(
        model_id="claude-haiku-4-5-20251001",
        input_cost_per_million=1.0,
        output_cost_per_million=5.0,
    ),
    ModelTier.SONNET: ModelDefinition(
        model_id="claude-sonnet-5",
        input_cost_per_million=2.0,
        output_cost_per_million=10.0,
    ),
    ModelTier.OPUS: ModelDefinition(
        model_id="claude-opus-5",
        input_cost_per_million=5.0,
        output_cost_per_million=25.0,
    ),
}


class ModelResponseError(ValueError):
    pass


class AnthropicGateway:
    def __init__(
        self,
        *,
        settings: AgentSettings,
        budget: BudgetTracker,
        client: Any | None = None,
    ) -> None:
        self.settings = settings
        self.budget = budget
        self.client = client or Anthropic()

    def complete_json(
        self,
        *,
        stage: Stage,
        tier: ModelTier,
        system: str,
        payload: dict[str, Any],
        response_model: type[ResponseModel],
        reason: str,
    ) -> ResponseModel:
        definition = MODEL_CATALOG[tier]
        schema = response_model.model_json_schema()
        prompt = (
            "Return only one JSON object that validates against this JSON Schema. "
            "Do not wrap it in Markdown.\n\n"
            f"JSON Schema:\n{json.dumps(schema, separators=(',', ':'))}\n\n"
            f"Input:\n{json.dumps(payload, separators=(',', ':'), default=str)}"
        )
        response = self.client.messages.create(
            model=definition.model_id,
            max_tokens=self.settings.limits.max_output_tokens_per_call,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        input_tokens = int(response.usage.input_tokens)
        output_tokens = int(response.usage.output_tokens)
        if input_tokens > self.settings.limits.max_input_tokens_per_call:
            raise ModelResponseError(
                "Model call exceeded configured input token limit: "
                f"{input_tokens} > {self.settings.limits.max_input_tokens_per_call}"
            )

        usage = UsageRecord(
            stage=stage,
            model=tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=self._estimate_cost(
                definition,
                input_tokens,
                output_tokens,
            ),
            reason=reason,
        )
        self.budget.record(usage)

        text = self._text_content(response)
        try:
            return response_model.model_validate_json(text)
        except ValueError as error:
            raise ModelResponseError(
                f"Invalid structured response for {response_model.__name__}: {error}"
            ) from error

    @staticmethod
    def _text_content(response: Any) -> str:
        text_blocks = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        if not text_blocks:
            raise ModelResponseError("Anthropic response contained no text")
        return "".join(text_blocks).strip()

    @staticmethod
    def _estimate_cost(
        definition: ModelDefinition,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        return (
            input_tokens * definition.input_cost_per_million
            + output_tokens * definition.output_cost_per_million
        ) / 1_000_000
