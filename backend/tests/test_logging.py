import logging

import pytest
from fakes import FakeChat, FakeClassifier
from fastapi.testclient import TestClient

from app.logging_config import MAX_ERROR_CHARS, configure_logging, describe_error
from app.main import app
from app.schemas import RouteVerdict

MARKER = "ZZSECRETMARKERZZ"
POST = f"you are awful {MARKER}"


@pytest.fixture(autouse=True)
def router(no_real_llm, set_router):
    return set_router(FakeClassifier(RouteVerdict(branch="mixed", reason="x")))


def text_outside_transcript(caplog):
    """Everything logged except the app.transcript lines, which carry chat text on purpose."""
    return "\n".join(
        r.getMessage() for r in caplog.records if r.name != "app.transcript"
    )


# --- describe_error --------------------------------------------------------


def test_describe_error_has_type_and_message():
    assert describe_error(RuntimeError("boom")) == "RuntimeError: boom"


def test_describe_error_reads_status_code_attribute():
    class ApiError(Exception):
        status_code = 401

    assert describe_error(ApiError("User not found.")) == (
        "ApiError status=401: User not found."
    )


def test_describe_error_reads_status_from_response():
    class Response:
        status_code = 429

    class HttpError(Exception):
        response = Response()

    assert describe_error(HttpError("slow down")) == "HttpError status=429: slow down"


def test_describe_error_truncates_long_messages():
    out = describe_error(RuntimeError("x" * 1000))
    assert out == "RuntimeError: " + "x" * MAX_ERROR_CHARS


def test_describe_error_is_a_single_line():
    assert describe_error(RuntimeError("a\n\n  b\tc")) == "RuntimeError: a b c"


# --- configure_logging -----------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [("debug", "DEBUG"), ("WARNING", "WARNING"), ("nonsense", "INFO"), ("", "INFO")],
)
def test_log_level_from_env(monkeypatch, value, expected):
    captured = {}
    monkeypatch.setattr(logging, "basicConfig", lambda **kw: captured.update(kw))
    monkeypatch.setenv("LOG_LEVEL", value)
    configure_logging()
    assert captured["level"] == expected


def test_log_level_defaults_to_info(monkeypatch):
    captured = {}
    monkeypatch.setattr(logging, "basicConfig", lambda **kw: captured.update(kw))
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    configure_logging()
    assert captured["level"] == "INFO"


# --- startup ---------------------------------------------------------------


def test_startup_logs_a_summary_without_the_key(caplog):
    caplog.set_level(logging.INFO)
    with TestClient(app):
        pass
    assert (
        "startup: classifier_model=test/classifier chat_model=test/chat "
        "api_key_configured=True"
    ) in caplog.text
    assert "is not set" not in caplog.text
    assert "sk-or-v1" not in caplog.text


def test_startup_warns_about_unset_variables(caplog, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("CHAT_MODEL", "")
    caplog.set_level(logging.INFO)
    with TestClient(app):
        pass
    assert "api_key_configured=False" in caplog.text
    assert "chat_model=<unset>" in caplog.text
    assert "startup: OPENROUTER_API_KEY is not set" in caplog.text
    assert "startup: CHAT_MODEL is not set" in caplog.text
    assert "CLASSIFIER_MODEL is not set" not in caplog.text


# --- classify logging ------------------------------------------------------


def test_classify_success_logs_metadata_only(client, set_classifier, verdict, caplog):
    caplog.set_level(logging.INFO)
    set_classifier(FakeClassifier(result=verdict))
    client.post("/classify", json={"text": POST})

    assert "classify: ok model=test/classifier" in caplog.text
    assert f"chars={len(POST)}" in caplog.text
    assert "harmful=True category=hate severity=high" in caplog.text
    assert MARKER not in caplog.text


def test_classify_failure_logs_cause_but_not_text_or_key(client, set_classifier, caplog):
    caplog.set_level(logging.INFO)
    set_classifier(FakeClassifier(exc=RuntimeError("401 Unauthorized")))
    client.post("/classify", json={"text": POST})

    assert "classify: LLM call failed" in caplog.text
    assert "RuntimeError: 401 Unauthorized" in caplog.text
    assert MARKER not in caplog.text
    assert "sk-or-v1" not in caplog.text


def test_classify_wrong_result_type_is_logged(client, set_classifier, caplog):
    caplog.set_level(logging.INFO)
    set_classifier(FakeClassifier(result=None))
    client.post("/classify", json={"text": POST})

    assert "classify: unexpected result type=NoneType" in caplog.text
    assert MARKER not in caplog.text


def test_classify_unconfigured_is_logged_as_a_warning(client, monkeypatch, caplog):
    monkeypatch.setenv("CLASSIFIER_MODEL", "")
    caplog.set_level(logging.INFO)
    client.post("/classify", json={"text": POST})

    assert "classify: not configured (api_key=True classifier_model=False)" in caplog.text
    assert MARKER not in caplog.text


# --- chat logging ----------------------------------------------------------


def chat_body(verdict_json, history=({"role": "user", "text": "hello"},)):
    return {"post": POST, "verdict": verdict_json, "history": list(history)}


def test_chat_logs_start_and_completion_without_text(
    client, set_chat, verdict_json, caplog
):
    caplog.set_level(logging.INFO)
    set_chat(FakeChat(["a", "b"]))
    client.post("/chat", json=chat_body(verdict_json))

    assert "chat: stream started model=test/chat history=1" in caplog.text
    assert "chat: stream done model=test/chat chunks=2" in caplog.text
    assert MARKER not in text_outside_transcript(caplog)


def test_chat_text_is_only_logged_by_the_transcript_logger(
    client, set_chat, verdict_json, caplog
):
    caplog.set_level(logging.DEBUG)
    set_chat(FakeChat(["ok"]))
    history = [{"role": "user", "text": f"private thoughts {MARKER}"}]
    client.post("/chat", json=chat_body(verdict_json, history))

    assert "history=1" in caplog.text
    assert MARKER not in text_outside_transcript(caplog)
    transcript = [r.getMessage() for r in caplog.records if r.name == "app.transcript"]
    assert len(transcript) == 1 and MARKER in transcript[0]


def test_menu_message_quotes_the_post_only_on_the_transcript_logger(
    client, verdict_json, caplog
):
    caplog.set_level(logging.DEBUG)
    history = []
    for i in range(4):
        history += [
            {"role": "ai", "text": f"bot {i}"},
            {"role": "user", "text": f"user {i}"},
        ]
    r = client.post("/chat", json=chat_body(verdict_json, history))

    assert MARKER in r.text  # the fixed menu message quotes the post
    assert MARKER not in text_outside_transcript(caplog)
    transcript = [r.getMessage() for r in caplog.records if r.name == "app.transcript"]
    assert len(transcript) == 1 and MARKER in transcript[0]


def test_router_reason_is_only_logged_by_the_transcript_logger(
    client, set_chat, router, verdict_json, caplog
):
    caplog.set_level(logging.DEBUG)
    set_chat(FakeChat(["ok"]))
    router.result = RouteVerdict(branch="joke", reason=f"quotes {MARKER}")
    client.post("/chat", json=chat_body(verdict_json))

    assert "chat: routed branch=joke" in caplog.text
    assert MARKER not in text_outside_transcript(caplog)
    transcript = [r.getMessage() for r in caplog.records if r.name == "app.transcript"]
    assert len(transcript) == 1 and MARKER in transcript[0]


def test_chat_start_failure_is_logged_without_text(
    client, set_chat, verdict_json, caplog
):
    caplog.set_level(logging.INFO)
    set_chat(FakeChat(fail_before_first=True))
    client.post("/chat", json=chat_body(verdict_json))

    assert "chat: failed to start model=test/chat history=1" in caplog.text
    assert "ConnectionError: upstream down" in caplog.text
    assert MARKER not in text_outside_transcript(caplog)


def test_chat_unconfigured_is_logged_as_a_warning(
    client, monkeypatch, verdict_json, caplog
):
    monkeypatch.setenv("CHAT_MODEL", "")
    caplog.set_level(logging.INFO)
    client.post("/chat", json=chat_body(verdict_json))

    assert "chat: not configured (api_key=True chat_model=False)" in caplog.text
