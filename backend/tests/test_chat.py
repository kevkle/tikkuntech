import logging

import pytest
from fakes import FakeChat, FakeClassifier
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.prompts.support_chat import (
    BRANCH_ADDENDA,
    CLOSING_INSTRUCTION,
    FIXED_OPENING,
)
from app.schemas import RouteVerdict


def user(text):
    return {"role": "user", "text": text}


def ai(text):
    return {"role": "ai", "text": text}


def route(branch):
    return RouteVerdict(branch=branch, reason="x")


def convo(bot_turns):
    """History with `bot_turns` bot messages, each answered by the user."""
    history = []
    for i in range(bot_turns):
        history += [ai(f"bot {i}"), user(f"user {i}")]
    return history


@pytest.fixture
def body(verdict_json):
    return {"post": "a draft", "verdict": verdict_json, "history": [user("hello")]}


@pytest.fixture(autouse=True)
def router(no_real_llm, set_router):
    """Default router: 'mixed'. Tests change `.result` / `.exc` to steer it."""
    return set_router(FakeClassifier(route("mixed")))


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


# --- fixed opening ---------------------------------------------------------


def test_empty_history_returns_the_fixed_opening_without_calling_any_model(
    client, set_chat, router, body
):
    fake = set_chat(FakeChat(["should not be used"]))
    body["history"] = []
    r = client.post("/chat", json=body)

    assert r.status_code == 200
    assert r.text == FIXED_OPENING
    assert fake.calls == []
    assert router.calls == []


def test_fixed_opening_keeps_the_no_buffering_headers(client, body):
    body["history"] = []
    r = client.post("/chat", json=body)
    assert r.headers["content-type"].startswith("text/plain")
    assert r.headers["cache-control"] == "no-cache"
    assert r.headers["x-accel-buffering"] == "no"


# --- what is sent to the model --------------------------------------------


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


def test_system_prompt_carries_the_post_and_verdict(client, set_chat, body):
    fake = set_chat(FakeChat(["ok"]))
    client.post("/chat", json=body)

    system = fake.calls[0][0].content
    assert "a draft" in system
    assert "Category: hate" in system
    assert "Severity: high" in system


# --- routing ---------------------------------------------------------------


@pytest.mark.parametrize("branch", ["belief", "grievance", "joke", "mixed", "disengage"])
def test_router_label_selects_the_matching_addendum(
    client, set_chat, router, body, branch
):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route(branch)
    client.post("/chat", json=body)

    system = fake.calls[0][0].content
    assert BRANCH_ADDENDA[branch] in system
    for other in BRANCH_ADDENDA:
        if other != branch:
            assert BRANCH_ADDENDA[other] not in system


def test_router_sees_the_post_and_only_the_last_three_messages(
    client, set_chat, router, body
):
    set_chat(FakeChat(["ok"]))
    body["history"] = [
        ai("first bot"),
        user("first user"),
        ai("second bot"),
        user("second user"),
        ai("third bot"),
        user("third user"),
    ]
    client.post("/chat", json=body)

    system_msg, human_msg = router.calls[0]
    assert isinstance(system_msg, SystemMessage)
    text = human_msg.content
    assert "a draft" in text
    for kept in ("second user", "third bot", "third user"):
        assert kept in text
    for dropped in ("first bot", "first user", "second bot"):
        assert dropped not in text


def test_router_failure_falls_back_to_mixed_and_is_logged(
    client, set_chat, router, body, caplog
):
    caplog.set_level(logging.WARNING, logger="app.chat")
    fake = set_chat(FakeChat(["ok"]))
    router.exc = RuntimeError("router down")
    r = client.post("/chat", json=body)

    assert r.status_code == 200
    assert r.text == "ok"
    assert BRANCH_ADDENDA["mixed"] in fake.calls[0][0].content
    assert any("chat: router failed" in rec.getMessage() for rec in caplog.records)


def test_router_factory_exception_falls_back_to_mixed(
    client, set_chat, monkeypatch, body
):
    def broken():
        raise RuntimeError("bad router config")

    monkeypatch.setattr("app.routers.chat.get_router_llm", broken)
    fake = set_chat(FakeChat(["ok"]))
    r = client.post("/chat", json=body)

    assert r.status_code == 200
    assert BRANCH_ADDENDA["mixed"] in fake.calls[0][0].content


def test_router_returning_the_wrong_type_falls_back_to_mixed(
    client, set_chat, router, body
):
    fake = set_chat(FakeChat(["ok"]))
    router.result = "not a RouteVerdict"
    r = client.post("/chat", json=body)

    assert r.status_code == 200
    assert BRANCH_ADDENDA["mixed"] in fake.calls[0][0].content


# --- turn cap --------------------------------------------------------------


@pytest.mark.parametrize("bot_turns", [1, 5, 6])
def test_before_the_eighth_bot_message_there_is_no_closing_instruction(
    client, set_chat, body, bot_turns
):
    fake = set_chat(FakeChat(["ok"]))
    body["history"] = convo(bot_turns)
    client.post("/chat", json=body)

    assert CLOSING_INSTRUCTION not in fake.calls[0][0].content


@pytest.mark.parametrize("bot_turns", [7, 8, 9])
def test_from_the_eighth_bot_message_on_the_reply_is_a_warm_close(
    client, set_chat, body, bot_turns
):
    fake = set_chat(FakeChat(["ok"]))
    body["history"] = convo(bot_turns)
    client.post("/chat", json=body)

    assert CLOSING_INSTRUCTION in fake.calls[0][0].content


# --- transcript ------------------------------------------------------------


def transcript_lines(caplog):
    return [r.getMessage() for r in caplog.records if r.name == "app.transcript"]


def test_transcript_logs_branch_turn_user_message_and_full_bot_reply(
    client, set_chat, router, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["Hel", "lo"]))
    router.result = route("grievance")
    body["history"] = [ai(FIXED_OPENING), user("i am angry")]
    client.post("/chat", json=body)

    assert transcript_lines(caplog) == [
        "transcript: branch=grievance turn=2 user='i am angry' bot='Hello'"
    ]


def test_transcript_logs_the_fixed_opening(client, body, caplog):
    caplog.set_level(logging.INFO, logger="app.transcript")
    body["history"] = []
    client.post("/chat", json=body)

    assert transcript_lines(caplog) == [
        f"transcript: branch=opening turn=1 user=None bot={FIXED_OPENING!r}"
    ]


def test_transcript_stays_on_one_line_when_text_has_newlines(
    client, set_chat, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["one\ntwo"]))
    body["history"] = [user("a\nb")]
    client.post("/chat", json=body)

    (line,) = transcript_lines(caplog)
    assert "\n" not in line
    assert "user='a\\nb'" in line and "bot='one\\ntwo'" in line


def test_transcript_is_not_written_when_the_stream_fails_midway(
    client, set_chat, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["one", "two", "three"], fail_after=2))
    try:
        client.post("/chat", json=body)
    except Exception:
        pass  # an aborted stream may surface as an exception in the test client

    assert transcript_lines(caplog) == []


def test_transcript_is_not_written_when_the_chat_fails_to_start(
    client, set_chat, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(fail_before_first=True))
    client.post("/chat", json=body)

    assert transcript_lines(caplog) == []


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
