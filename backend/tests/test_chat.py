import logging

import pytest
from fakes import FakeChat
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.prompts.support_chat import OPENING_INSTRUCTION


@pytest.fixture
def body(verdict_json):
    return {"post": "a draft", "verdict": verdict_json, "history": []}


def user(text):
    return {"role": "user", "text": text}


def ai(text):
    return {"role": "ai", "text": text}


# --- validation ------------------------------------------------------------


def test_history_ending_with_ai_is_422(client, body):
    body["history"] = [user("a"), ai("b")]
    assert client.post("/chat", json=body).status_code == 422


def test_too_many_messages_is_422(client, body):
    body["history"] = [user("a")] * 41
    assert client.post("/chat", json=body).status_code == 422


def test_empty_post_is_422(client, body):
    body["post"] = ""
    assert client.post("/chat", json=body).status_code == 422


def test_missing_verdict_is_422(client, body):
    del body["verdict"]
    assert client.post("/chat", json=body).status_code == 422


@pytest.mark.parametrize("var", ["OPENROUTER_API_KEY", "CHAT_MODEL"])
def test_unconfigured_is_503(client, monkeypatch, body, var):
    monkeypatch.setenv(var, "")
    r = client.post("/chat", json=body)
    assert r.status_code == 503
    assert r.json() == {"detail": "Chat is not configured"}


# --- what is sent to the model --------------------------------------------


def test_opening_request_sends_system_prompt_and_opening_instruction(
    client, set_chat, body
):
    fake = set_chat(FakeChat(["hi"]))
    client.post("/chat", json=body)

    messages = fake.calls[0]
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == OPENING_INSTRUCTION


def test_history_roles_map_to_messages_in_order(client, set_chat, body):
    fake = set_chat(FakeChat(["ok"]))
    body["history"] = [ai("opening"), user("my reply"), ai("follow-up"), user("more")]
    client.post("/chat", json=body)

    messages = fake.calls[0]
    assert [type(m) for m in messages] == [
        SystemMessage,
        AIMessage,
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]
    assert [m.content for m in messages[1:]] == [
        "opening",
        "my reply",
        "follow-up",
        "more",
    ]


def test_opening_instruction_is_not_added_when_history_exists(client, set_chat, body):
    fake = set_chat(FakeChat(["ok"]))
    body["history"] = [user("hello")]
    client.post("/chat", json=body)

    contents = [m.content for m in fake.calls[0]]
    assert OPENING_INSTRUCTION not in contents


def test_system_prompt_carries_the_post_and_verdict(client, set_chat, body):
    fake = set_chat(FakeChat(["ok"]))
    client.post("/chat", json=body)

    system = fake.calls[0][0].content
    assert "a draft" in system
    assert "Category: hate" in system
    assert "Severity: high" in system


# --- streaming -------------------------------------------------------------


def test_streams_chunks_in_order(client, set_chat, body):
    set_chat(FakeChat(["Hel", "lo ", "there"]))
    r = client.post("/chat", json=body)
    assert r.status_code == 200
    assert r.text == "Hello there"


def test_response_headers_disable_buffering(client, set_chat, body):
    set_chat(FakeChat(["hi"]))
    r = client.post("/chat", json=body)
    assert r.headers["content-type"].startswith("text/plain")
    assert r.headers["cache-control"] == "no-cache"
    assert r.headers["x-accel-buffering"] == "no"


def test_list_style_chunk_content_is_joined(client, set_chat, body):
    set_chat(
        FakeChat(
            [[{"type": "text", "text": "Hi"}, {"type": "text", "text": " there"}], "!"]
        )
    )
    assert client.post("/chat", json=body).text == "Hi there!"


def test_empty_stream_is_200_with_empty_body(client, set_chat, body):
    set_chat(FakeChat([]))
    r = client.post("/chat", json=body)
    assert r.status_code == 200
    assert r.text == ""


# --- failures --------------------------------------------------------------


def test_failure_before_first_chunk_is_502(client, set_chat, body):
    set_chat(FakeChat(fail_before_first=True))
    r = client.post("/chat", json=body)
    assert r.status_code == 502
    assert r.json() == {"detail": "Chat failed"}


def test_factory_exception_is_502(client, monkeypatch, body):
    def broken():
        raise RuntimeError("bad model config")

    monkeypatch.setattr("app.routers.chat.get_chat_llm", broken)
    r = client.post("/chat", json=body)
    assert r.status_code == 502
    assert "bad model config" not in r.text


def test_mid_stream_failure_stops_the_stream_and_is_logged(
    client, set_chat, body, caplog
):
    caplog.set_level(logging.ERROR, logger="app.chat")
    set_chat(FakeChat(["one", "two", "three"], fail_after=2))

    text = ""
    try:
        text = client.post("/chat", json=body).text
    except Exception:
        pass  # an aborted stream may surface as an exception in the test client

    assert "three" not in text
    assert any("chat: stream failed" in rec.getMessage() for rec in caplog.records)
