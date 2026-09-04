from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agentic_triage.budget import BudgetTracker
from agentic_triage.config import AgentLimits, AgentSettings
from agentic_triage.model_gateway import (
    MODEL_CATALOG,
    AnthropicGateway,
    ModelResponseError,
)
from agentic_triage.models import ModelTier, Stage


class StructuredAnswer(BaseModel):
    answer: str
    confidence: float


class FakeMessages:
    def __init__(self, text: str, input_tokens: int = 100, output_tokens: int = 20):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.text)],
            usage=SimpleNamespace(
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
            ),
        )


def gateway(messages: FakeMessages, settings: AgentSettings | None = None):
    client = SimpleNamespace(messages=messages)
    budget = BudgetTracker(max_cost_usd=1.0)
    return (
        AnthropicGateway(
            settings=settings or AgentSettings(),
            budget=budget,
            client=client,
        ),
        budget,
    )


def test_validates_json_and_records_haiku_cost() -> None:
    messages = FakeMessages('{"answer":"use the tag association","confidence":0.9}')
    model_gateway, budget = gateway(messages)

    answer = model_gateway.complete_json(
        stage=Stage.DIAGNOSE,
        tier=ModelTier.HAIKU,
        system="Diagnose the bug.",
        payload={"issue": "wrong filter"},
        response_model=StructuredAnswer,
        reason="routine diagnosis",
    )

    assert answer.answer == "use the tag association"
    assert messages.calls[0]["model"] == MODEL_CATALOG[ModelTier.HAIKU].model_id
    assert budget.records[0].model is ModelTier.HAIKU
    assert budget.spent_usd == pytest.approx(0.0002)


def test_rejects_invalid_structured_response() -> None:
    model_gateway, _ = gateway(FakeMessages("not json"))

    with pytest.raises(ModelResponseError, match="Invalid structured response"):
        model_gateway.complete_json(
            stage=Stage.DIAGNOSE,
            tier=ModelTier.HAIKU,
            system="Diagnose the bug.",
            payload={},
            response_model=StructuredAnswer,
            reason="routine diagnosis",
        )


def test_accepts_single_markdown_fenced_json_object() -> None:
    model_gateway, _ = gateway(
        FakeMessages(
            '```json\n{"answer":"bounded context","confidence":0.8}\n```'
        )
    )

    answer = model_gateway.complete_json(
        stage=Stage.CONTEXT,
        tier=ModelTier.HAIKU,
        system="Plan context.",
        payload={},
        response_model=StructuredAnswer,
        reason="context planning",
    )

    assert answer.answer == "bounded context"


def test_rejects_input_over_configured_limit() -> None:
    settings = AgentSettings(
        limits=AgentLimits(max_input_tokens_per_call=10)
    )
    model_gateway, _ = gateway(
        FakeMessages('{"answer":"x","confidence":0.5}', input_tokens=11),
        settings,
    )

    with pytest.raises(ModelResponseError, match="input token limit"):
        model_gateway.complete_json(
            stage=Stage.DIAGNOSE,
            tier=ModelTier.HAIKU,
            system="Diagnose the bug.",
            payload={},
            response_model=StructuredAnswer,
            reason="routine diagnosis",
        )
