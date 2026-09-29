import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest, ClassifyRequest, Verdict


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


def test_verdict_requires_all_fields():
    with pytest.raises(ValidationError):
        Verdict(harmful=True)


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
