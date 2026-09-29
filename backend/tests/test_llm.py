import pytest

from app import llm
from app.schemas import RouteVerdict, Verdict


class CapturingChatOpenRouter:
    """Stands in for ChatOpenRouter so no client is built and nothing touches the network."""

    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.structured_schema = None
        CapturingChatOpenRouter.instances.append(self)

    def with_structured_output(self, schema):
        self.structured_schema = schema
        return self


@pytest.fixture(autouse=True)
def capture_client(monkeypatch):
    CapturingChatOpenRouter.instances = []
    monkeypatch.setattr(llm, "ChatOpenRouter", CapturingChatOpenRouter)


def test_chat_llm_uses_env_model_and_low_reasoning_effort():
    model = llm.get_chat_llm()
    assert model.kwargs == {
        "model": "test/chat",
        "temperature": 0.7,
        "reasoning": {"effort": "low"},
    }


def test_chat_llm_never_disables_reasoning():
    """OpenRouter rejects a disabled setting for this model with a 400."""
    reasoning = llm.get_chat_llm().kwargs["reasoning"]
    assert reasoning.get("enabled") is not False
    assert reasoning.get("effort") != "none"


def test_classifier_llm_uses_env_model_and_is_deterministic():
    model = llm.get_classifier_llm()
    assert model.kwargs == {"model": "test/classifier", "temperature": 0}


def test_classifier_llm_is_bound_to_the_verdict_schema():
    assert llm.get_classifier_llm().structured_schema is Verdict


def test_router_llm_reuses_the_classifier_model_and_is_deterministic():
    model = llm.get_router_llm()
    assert model.kwargs == {"model": "test/classifier", "temperature": 0}


def test_router_llm_is_bound_to_the_route_verdict_schema():
    assert llm.get_router_llm().structured_schema is RouteVerdict


def test_factories_read_models_from_the_environment(monkeypatch):
    monkeypatch.setenv("CHAT_MODEL", "other/chat-model")
    monkeypatch.setenv("CLASSIFIER_MODEL", "other/classifier-model")
    assert llm.get_chat_llm().kwargs["model"] == "other/chat-model"
    assert llm.get_classifier_llm().kwargs["model"] == "other/classifier-model"
    assert llm.get_router_llm().kwargs["model"] == "other/classifier-model"
