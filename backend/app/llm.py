"""LangChain model factories for OpenRouter."""

import logging

from langchain_openrouter import ChatOpenRouter

from app.config import load_settings
from app.schemas import Verdict

logger = logging.getLogger("app.llm")


def get_classifier_llm():
    """Chat model bound to the Verdict schema (function calling). Reads OPENROUTER_API_KEY from env."""
    settings = load_settings()
    logger.debug("building classifier llm model=%s", settings.classifier_model)
    model = ChatOpenRouter(model=settings.classifier_model, temperature=0)
    return model.with_structured_output(Verdict)


def get_chat_llm():
    """Plain chat model for the supportive conversation. Reads OPENROUTER_API_KEY from env."""
    settings = load_settings()
    logger.debug("building chat llm model=%s", settings.chat_model)
    # Reasoning can't be disabled on this endpoint ("mandatory"). With the default effort,
    # flagged posts think for ~4s and then deliver the reply in one burst; "low" starts
    # in ~1.5s and streams progressively.
    return ChatOpenRouter(
        model=settings.chat_model,
        temperature=0.7,
        reasoning={"effort": "low"},
    )
