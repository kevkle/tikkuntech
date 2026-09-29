"""LangChain model factories for OpenRouter."""

from langchain_openrouter import ChatOpenRouter

from app.config import load_settings
from app.schemas import Verdict


def get_classifier_llm():
    """Chat model bound to the Verdict schema (function calling). Reads OPENROUTER_API_KEY from env."""
    settings = load_settings()
    model = ChatOpenRouter(model=settings.classifier_model, temperature=0)
    return model.with_structured_output(Verdict)


def get_chat_llm():
    raise NotImplementedError("Phase 3")
