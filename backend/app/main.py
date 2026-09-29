import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import load_settings
from app.logging_config import configure_logging
from app.routers import chat, classify

configure_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = load_settings()
    logger.info(
        "startup: classifier_model=%s chat_model=%s api_key_configured=%s",
        s.classifier_model or "<unset>",
        s.chat_model or "<unset>",
        bool(s.openrouter_api_key),
    )
    for name, value in (
        ("OPENROUTER_API_KEY", s.openrouter_api_key),
        ("CLASSIFIER_MODEL", s.classifier_model),
        ("CHAT_MODEL", s.chat_model),
    ):
        if not value:
            logger.warning("startup: %s is not set", name)
    yield


app = FastAPI(title="TikkunTech backend", lifespan=lifespan)

app.include_router(classify.router)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
