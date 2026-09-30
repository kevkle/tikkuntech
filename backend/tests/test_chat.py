import asyncio
import logging

import pytest
from fakes import FakeChat, FakeClassifier
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.prompts.support_chat import (
    BRANCH_ADDENDA,
    CLOSING_INSTRUCTION,
    CONTINUE_NOTE,
    FIXED_OPENING,
    LISTEN_NOTE,
    RETURN_TO_POST_NOTE,
)
from app.routers.chat import chat
from app.schemas import ChatRequest, RouteVerdict


def user(text):
    return {"role": "user", "text": text}


def ai(text):
    return {"role": "ai", "text": text}


def route(branch, ready=False):
    return RouteVerdict(branch=branch, reason="x", ready=ready)


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


def test_user_name_reaches_the_system_prompt(client, set_chat, body):
    fake = set_chat(FakeChat(["ok"]))
    body["user_name"] = "Mark"
    client.post("/chat", json=body)

    assert "Person's name: Mark" in fake.calls[0][0].content


def test_no_user_name_means_no_name_line(client, set_chat, body):
    fake = set_chat(FakeChat(["ok"]))
    client.post("/chat", json=body)

    assert "Person's name" not in fake.calls[0][0].content


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


@pytest.mark.parametrize("bot_turns", [7, 8])
def test_the_eighth_bot_message_is_the_close_if_it_has_not_happened_yet(
    client, set_chat, body, bot_turns
):
    fake = set_chat(FakeChat(["ok"]))
    body["history"] = convo(bot_turns)
    r = client.post("/chat", json=body)

    assert CLOSING_INSTRUCTION in fake.calls[0][0].content
    assert r.headers["x-chat-phase"] == "close"
    assert "x-chat-menu" in r.headers


def test_after_the_close_the_chat_continues_without_another_close(client, set_chat, body):
    fake = set_chat(FakeChat(["ok"]))
    body["history"] = convo(9)
    body["last_phase"] = "close"
    client.post("/chat", json=body)

    system = fake.calls[0][0].content
    assert CLOSING_INSTRUCTION not in system
    assert CONTINUE_NOTE in system


@pytest.mark.parametrize("bot_turns", [7, 8, 9])
def test_disengage_gets_the_warm_close_at_the_cap_without_the_menu(
    client, set_chat, router, body, bot_turns
):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("disengage", ready=False)
    body["history"] = convo(bot_turns)
    r = client.post("/chat", json=body)

    assert CLOSING_INSTRUCTION in fake.calls[0][0].content
    assert "x-chat-menu" not in r.headers
    assert "x-chat-phase" not in r.headers


# --- stages and the option menu ---------------------------------------------
#
# Bot message N is written after `convo(N - 1)`. The return to the post (and then the
# close with the X-Chat-Menu header) follows it. The return happens when the router says
# the person is ready, from bot message 3 on, and at the latest on bot message 6; the
# close is the next bot message, or bot message 8 at the latest.

ALL_NOTES = (LISTEN_NOTE, RETURN_TO_POST_NOTE, CONTINUE_NOTE)


def only_note(system, note):
    assert note in system
    for other in ALL_NOTES:
        if other != note:
            assert other not in system


@pytest.mark.parametrize("bot_turns", [1, 2, 3, 4])
def test_not_ready_keeps_listening_without_the_menu(
    client, set_chat, router, body, bot_turns
):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("grievance", ready=False)
    body["history"] = convo(bot_turns)  # bot messages 2 to 5
    r = client.post("/chat", json=body)

    only_note(fake.calls[0][0].content, LISTEN_NOTE)
    assert "x-chat-menu" not in r.headers


@pytest.mark.parametrize("bot_turns", [2, 3, 4])
def test_ready_returns_to_the_post_without_the_menu(
    client, set_chat, router, body, bot_turns
):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("grievance", ready=True)
    body["history"] = convo(bot_turns)  # bot messages 3 to 5
    r = client.post("/chat", json=body)

    assert len(fake.calls) == 1  # a normal model reply, not a fixed message
    only_note(fake.calls[0][0].content, RETURN_TO_POST_NOTE)
    assert r.text == "ok"
    assert r.headers["x-chat-phase"] == "return"
    assert "x-chat-menu" not in r.headers


def test_ready_on_the_second_bot_message_is_too_early(client, set_chat, router, body):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("grievance", ready=True)
    body["history"] = convo(1)  # bot message 2
    r = client.post("/chat", json=body)

    only_note(fake.calls[0][0].content, LISTEN_NOTE)
    assert "x-chat-menu" not in r.headers


def test_the_fallback_returns_to_the_post_on_bot_message_six_even_if_not_ready(
    client, set_chat, router, body
):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("joke", ready=False)
    body["history"] = convo(5)  # bot message 6
    r = client.post("/chat", json=body)

    only_note(fake.calls[0][0].content, RETURN_TO_POST_NOTE)
    assert r.headers["x-chat-phase"] == "return"


def test_the_message_before_the_fallback_still_waits(client, set_chat, router, body):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("joke", ready=False)
    body["history"] = convo(4)  # bot message 5
    r = client.post("/chat", json=body)

    only_note(fake.calls[0][0].content, LISTEN_NOTE)
    assert "x-chat-menu" not in r.headers


@pytest.mark.parametrize("ready", [False, True])
def test_the_reply_after_the_return_is_the_close_with_the_menu(
    client, set_chat, router, body, ready
):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("belief", ready=ready)
    body["history"] = convo(3)  # bot message 4
    body["last_phase"] = "return"
    r = client.post("/chat", json=body)

    system = fake.calls[0][0].content
    assert CLOSING_INSTRUCTION in system
    assert not any(note in system for note in ALL_NOTES)
    assert r.headers["x-chat-phase"] == "close"
    assert r.headers["x-chat-menu"] == "belief"


@pytest.mark.parametrize("ready", [False, True])
def test_once_the_menu_is_shown_replies_continue_and_keep_the_header(
    client, set_chat, router, body, ready
):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("belief", ready=ready)
    body["history"] = convo(4)  # bot message 5
    body["last_phase"] = "close"
    r = client.post("/chat", json=body)

    only_note(fake.calls[0][0].content, CONTINUE_NOTE)
    assert r.headers["x-chat-menu"] == "belief"
    assert "x-chat-phase" not in r.headers


@pytest.mark.parametrize("branch", ["belief", "grievance", "joke", "mixed"])
def test_menu_header_names_the_routed_branch(client, set_chat, router, body, branch):
    set_chat(FakeChat(["ok"]))
    router.result = route(branch, ready=True)
    body["history"] = convo(3)
    body["last_phase"] = "return"
    r = client.post("/chat", json=body)

    assert r.headers["x-chat-menu"] == branch


def test_menu_reply_keeps_the_no_buffering_headers(client, set_chat, router, body):
    set_chat(FakeChat(["ok"]))
    router.result = route("mixed", ready=True)
    body["history"] = convo(3)
    body["last_phase"] = "return"
    r = client.post("/chat", json=body)

    assert r.headers["content-type"].startswith("text/plain")
    assert r.headers["cache-control"] == "no-cache"
    assert r.headers["x-accel-buffering"] == "no"


def test_disengage_never_gets_a_stage_note_or_the_menu(client, set_chat, router, body):
    fake = set_chat(FakeChat(["ok"]))
    router.result = route("disengage", ready=True)
    body["history"] = convo(5)  # past the fallback
    body["last_phase"] = "return"
    r = client.post("/chat", json=body)

    system = fake.calls[0][0].content
    assert BRANCH_ADDENDA["disengage"] in system
    assert not any(note in system for note in ALL_NOTES)
    assert "x-chat-menu" not in r.headers
    assert "x-chat-phase" not in r.headers


def test_the_closing_turn_has_no_stage_note_but_has_the_menu(client, set_chat, body):
    fake = set_chat(FakeChat(["ok"]))
    body["history"] = convo(7)  # bot message 8
    r = client.post("/chat", json=body)

    system = fake.calls[0][0].content
    assert CLOSING_INSTRUCTION in system
    assert not any(note in system for note in ALL_NOTES)
    assert "x-chat-menu" in r.headers


def test_a_router_failure_counts_as_not_ready(client, set_chat, router, body):
    fake = set_chat(FakeChat(["ok"]))
    router.exc = RuntimeError("router down")
    body["history"] = convo(3)  # bot message 4
    r = client.post("/chat", json=body)

    only_note(fake.calls[0][0].content, LISTEN_NOTE)
    assert "x-chat-menu" not in r.headers


def test_the_phase_is_logged_without_any_text(client, set_chat, router, body, caplog):
    caplog.set_level(logging.INFO, logger="app.chat")
    set_chat(FakeChat(["ok"]))
    router.result = route("grievance", ready=True)
    body["history"] = convo(3)
    client.post("/chat", json=body)

    lines = [r.getMessage() for r in caplog.records if r.name == "app.chat"]
    assert "chat: phase=return ready=True turn=4 last_phase=None" in lines
    assert not any("user 2" in line or "a draft" in line for line in lines)


# --- transcript ------------------------------------------------------------


def transcript_lines(caplog):
    return [r.getMessage() for r in caplog.records if r.name == "app.transcript"]


def test_transcript_logs_branch_turn_reason_user_message_and_full_bot_reply(
    client, set_chat, router, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["Hel", "lo"]))
    router.result = RouteVerdict(branch="grievance", reason="feels wronged", ready=False)
    body["history"] = [ai(FIXED_OPENING), user("i am angry")]
    client.post("/chat", json=body)

    assert transcript_lines(caplog) == [
        "transcript: branch=grievance turn=2 reason='feels wronged' "
        "user='i am angry' bot='Hello'"
    ]


def test_transcript_logs_the_fixed_opening(client, body, caplog):
    caplog.set_level(logging.INFO, logger="app.transcript")
    body["history"] = []
    client.post("/chat", json=body)

    assert transcript_lines(caplog) == [
        "transcript: branch=opening turn=1 reason=None user=None "
        f"bot={FIXED_OPENING!r}"
    ]


def test_transcript_marks_a_router_exception_as_a_fallback(
    client, set_chat, router, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["ok"]))
    router.exc = RuntimeError("router down")
    client.post("/chat", json=body)

    (line,) = transcript_lines(caplog)
    assert "branch=mixed" in line
    assert "reason='fallback: router unavailable'" in line


def test_transcript_marks_a_wrong_router_result_as_a_fallback(
    client, set_chat, router, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["ok"]))
    router.result = "not a RouteVerdict"
    client.post("/chat", json=body)

    (line,) = transcript_lines(caplog)
    assert "branch=mixed" in line
    assert "reason='fallback: router unavailable'" in line


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


def test_transcript_keeps_the_streamed_text_as_partial_when_the_stream_fails_midway(
    client, set_chat, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["one", "two", "three"], fail_after=2))
    try:
        client.post("/chat", json=body)
    except Exception:
        pass  # an aborted stream may surface as an exception in the test client

    (line,) = transcript_lines(caplog)
    assert line.endswith("bot='onetwo' partial=True")


def test_transcript_keeps_the_streamed_text_as_partial_when_the_client_disconnects(
    set_chat, verdict, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["one", "two", "three"]))
    req = ChatRequest(
        post="a draft", verdict=verdict, history=[{"role": "user", "text": "hello"}]
    )

    async def run():
        response = await chat(req)
        chunks = response.body_iterator
        assert await anext(chunks) == "one"
        await chunks.aclose()  # what a dropped connection does to the stream

    asyncio.run(run())

    (line,) = transcript_lines(caplog)
    assert line.endswith("user='hello' bot='one' partial=True")


def test_completed_transcript_lines_carry_no_partial_marker(
    client, set_chat, body, caplog
):
    caplog.set_level(logging.INFO, logger="app.transcript")
    set_chat(FakeChat(["all", " done"]))
    client.post("/chat", json=body)

    (line,) = transcript_lines(caplog)
    assert "partial" not in line


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
