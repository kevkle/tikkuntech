import pytest
from fakes import FakeClassifier
from langchain_core.messages import HumanMessage, SystemMessage

from app.prompts.classifier import CLASSIFIER_SYSTEM_PROMPT


def test_empty_text_is_422(client):
    assert client.post("/classify", json={"text": ""}).status_code == 422


def test_too_long_text_is_422(client):
    assert client.post("/classify", json={"text": "a" * 2001}).status_code == 422


def test_missing_text_is_422(client):
    assert client.post("/classify", json={}).status_code == 422


@pytest.mark.parametrize("var", ["OPENROUTER_API_KEY", "CLASSIFIER_MODEL"])
def test_unconfigured_is_503(client, monkeypatch, var):
    monkeypatch.setenv(var, "")
    r = client.post("/classify", json={"text": "hello"})
    assert r.status_code == 503
    assert r.json() == {"detail": "Classifier is not configured"}


def test_success_returns_the_verdict(client, set_classifier, verdict):
    set_classifier(FakeClassifier(result=verdict))
    r = client.post("/classify", json={"text": "some post"})
    assert r.status_code == 200
    assert r.json() == verdict.model_dump()


def test_text_at_the_length_limit_is_accepted(client, set_classifier, verdict):
    set_classifier(FakeClassifier(result=verdict))
    assert client.post("/classify", json={"text": "a" * 2000}).status_code == 200


def test_sends_system_prompt_then_wrapped_post(client, set_classifier, verdict):
    fake = set_classifier(FakeClassifier(result=verdict))
    client.post("/classify", json={"text": "some post"})

    system, human = fake.calls[0]
    assert isinstance(system, SystemMessage)
    assert system.content == CLASSIFIER_SYSTEM_PROMPT
    assert isinstance(human, HumanMessage)
    assert human.content == "<post>\nsome post\n</post>"


def test_llm_exception_is_502_with_generic_body(client, set_classifier):
    set_classifier(FakeClassifier(exc=RuntimeError("secret upstream detail")))
    r = client.post("/classify", json={"text": "hello"})
    assert r.status_code == 502
    assert r.json() == {"detail": "Classification failed"}
    assert "secret upstream detail" not in r.text


@pytest.mark.parametrize("bad_result", [None, {"harmful": True}, "plain text"])
def test_non_verdict_result_is_502(client, set_classifier, bad_result):
    """Fail closed: an unparseable result is never treated as a safe verdict."""
    set_classifier(FakeClassifier(result=bad_result))
    r = client.post("/classify", json={"text": "hello"})
    assert r.status_code == 502
    assert r.json() == {"detail": "Classification failed"}
