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


class SequencedMessages(FakeMessages):
    """Return a different response body for each successive call."""

    def __init__(self, texts: list[str]):
        super().__init__(texts[0])
        self.texts = texts

    def create(self, **kwargs):
        self.text = self.texts[min(len(self.calls), len(self.texts) - 1)]
        return super().create(**kwargs)


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


def test_repairs_a_schema_violation_on_a_second_attempt() -> None:
    messages = SequencedMessages([
        '{"answer":"first","confidence":"not-a-number"}',
        '{"answer":"corrected","confidence":0.7}',
    ])
    model_gateway, budget = gateway(messages)

    answer = model_gateway.complete_json(
        stage=Stage.CONTEXT,
        tier=ModelTier.HAIKU,
        system="Plan context.",
        payload={},
        response_model=StructuredAnswer,
        reason="context planning",
    )

    assert answer.answer == "corrected"
    assert len(messages.calls) == 2
    assert "failed schema validation" in messages.calls[1]["messages"][-1]["content"]
    assert budget.records[1].reason.endswith("(schema repair)")


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
