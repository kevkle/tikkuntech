import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest, ClassifyRequest, RouteVerdict, Verdict


def verdict_dict(**overrides):
    base = dict(harmful=True, category="hate", severity="high", reason="x")
    base.update(overrides)
    return base


def chat_dict(**overrides):
    base = dict(post="a draft", verdict=verdict_dict(), history=[])
    base.update(overrides)
    return base


def msg(role, text="hi"):
    return {"role": role, "text": text}


# --- Verdict ---------------------------------------------------------------


def test_verdict_accepts_valid_values():
    v = Verdict(**verdict_dict())
    assert v.category == "hate"


@pytest.mark.parametrize("field,value", [("category", "spam"), ("severity", "critical")])
def test_verdict_rejects_unknown_values(field, value):
    with pytest.raises(ValidationError):
        Verdict(**verdict_dict(**{field: value}))


@pytest.mark.parametrize("language", ["en", "ar", "fr", "de", None])
def test_verdict_accepts_a_post_language_or_none(language):
    assert Verdict(**verdict_dict(language=language)).language == language


def test_verdict_post_language_defaults_to_none():
    assert Verdict(**verdict_dict()).language is None


def test_verdict_rejects_an_unsupported_post_language():
    with pytest.raises(ValidationError):
        Verdict(**verdict_dict(language="he"))


def test_verdict_requires_all_fields():
    with pytest.raises(ValidationError):
        Verdict(harmful=True)


# --- RouteVerdict ----------------------------------------------------------


@pytest.mark.parametrize(
    "branch", ["belief", "grievance", "joke", "mixed", "disengage"]
)
def test_route_verdict_accepts_every_branch(branch):
    assert RouteVerdict(branch=branch, reason="x", ready=False).branch == branch


@pytest.mark.parametrize("branch", ["angry", "unclear", "crisis"])
def test_route_verdict_rejects_unknown_branch(branch):
    with pytest.raises(ValidationError):
        RouteVerdict(branch=branch, reason="x", ready=False)


def test_route_verdict_requires_ready():
    with pytest.raises(ValidationError):
        RouteVerdict(branch="joke", reason="x")


@pytest.mark.parametrize("ready", [True, False])
def test_route_verdict_keeps_ready(ready):
    assert RouteVerdict(branch="joke", reason="x", ready=ready).ready is ready


def test_route_verdict_requires_all_fields():
    with pytest.raises(ValidationError):
        RouteVerdict(branch="joke")


# --- ClassifyRequest -------------------------------------------------------


@pytest.mark.parametrize("text", ["", "a" * 2001])
def test_classify_request_rejects_bad_length(text):
    with pytest.raises(ValidationError):
        ClassifyRequest(text=text)


@pytest.mark.parametrize("text", ["a", "a" * 2000])
def test_classify_request_accepts_limits(text):
    assert ClassifyRequest(text=text).text == text


# --- ChatRequest -----------------------------------------------------------


def test_chat_request_allows_empty_history():
    assert ChatRequest(**chat_dict()).history == []


def test_chat_request_last_phase_defaults_to_none():
    assert ChatRequest(**chat_dict()).last_phase is None


@pytest.mark.parametrize("phase", ["return", "close"])
def test_chat_request_accepts_a_last_phase(phase):
    assert ChatRequest(**chat_dict(last_phase=phase)).last_phase == phase


def test_chat_request_rejects_an_unknown_last_phase():
    with pytest.raises(ValidationError):
        ChatRequest(**chat_dict(last_phase="listen"))


def test_chat_request_user_name_defaults_to_none():
    assert ChatRequest(**chat_dict()).user_name is None


def test_chat_request_accepts_a_user_name():
    assert ChatRequest(**chat_dict(user_name="Mark")).user_name == "Mark"


def test_chat_request_rejects_a_long_user_name():
    with pytest.raises(ValidationError):
        ChatRequest(**chat_dict(user_name="a" * 51))


def test_chat_request_language_defaults_to_english():
    assert ChatRequest(**chat_dict()).language == "en"


@pytest.mark.parametrize("language", ["en", "ar", "fr", "de"])
def test_chat_request_accepts_a_supported_language(language):
    assert ChatRequest(**chat_dict(language=language)).language == language


@pytest.mark.parametrize("language", ["he", "es", "EN", ""])
def test_chat_request_rejects_an_unsupported_language(language):
    with pytest.raises(ValidationError):
        ChatRequest(**chat_dict(language=language))


def test_chat_history_ending_with_user_is_valid():
    req = ChatRequest(**chat_dict(history=[msg("user"), msg("ai"), msg("user")]))
    assert len(req.history) == 3


def test_chat_history_must_end_with_user():
    with pytest.raises(ValidationError, match="end with a user message"):
        ChatRequest(**chat_dict(history=[msg("user"), msg("ai")]))


def test_chat_history_allows_40_messages():
    # Alternating roles, ending with a user message.
    history = [msg("ai" if i % 2 == 0 else "user") for i in range(40)]
    assert len(ChatRequest(**chat_dict(history=history)).history) == 40


def test_chat_history_rejects_41_messages():
    with pytest.raises(ValidationError):
        ChatRequest(**chat_dict(history=[msg("user")] * 41))


@pytest.mark.parametrize("post", ["", "a" * 2001])
def test_chat_post_limits(post):
    with pytest.raises(ValidationError):
        ChatRequest(**chat_dict(post=post))


@pytest.mark.parametrize("text", ["", "a" * 2001])
def test_chat_message_text_limits(text):
    with pytest.raises(ValidationError):
        ChatRequest(**chat_dict(history=[msg("user", text)]))


def test_chat_message_role_must_be_user_or_ai():
    with pytest.raises(ValidationError):
        ChatRequest(**chat_dict(history=[msg("system")]))
