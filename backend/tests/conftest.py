import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Verdict


class RealLLMCalled(BaseException):
    """BaseException so the routers' `except Exception` cannot swallow it."""


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-" + "0" * 64)
    monkeypatch.setenv("CLASSIFIER_MODEL", "test/classifier")
    monkeypatch.setenv("CHAT_MODEL", "test/chat")
    monkeypatch.delenv("LOG_LEVEL", raising=False)


@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch):
    """Fail loudly if a test reaches a real model factory instead of a fake."""

    def boom(*args, **kwargs):
        raise RealLLMCalled("a test tried to build a real LLM client")

    monkeypatch.setattr("app.routers.classify.get_classifier_llm", boom)
    monkeypatch.setattr("app.routers.chat.get_chat_llm", boom)


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def set_classifier(monkeypatch):
    def _set(fake):
        monkeypatch.setattr("app.routers.classify.get_classifier_llm", lambda: fake)
        return fake

    return _set


@pytest.fixture
def set_chat(monkeypatch):
    def _set(fake):
        monkeypatch.setattr("app.routers.chat.get_chat_llm", lambda: fake)
        return fake

    return _set


@pytest.fixture
def verdict():
    return Verdict(
        harmful=True, category="hate", severity="high", reason="Demeaning content."
    )


@pytest.fixture
def verdict_json(verdict):
    return verdict.model_dump()
