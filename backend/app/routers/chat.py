import logging
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import load_settings
from app.llm import get_chat_llm, get_router_llm
from app.logging_config import describe_error
from app.prompts.router import ROUTER_SYSTEM_PROMPT, build_router_input
from app.prompts.support_chat import FIXED_OPENING, build_system_prompt
from app.schemas import Branch, ChatRequest, RouteVerdict

logger = logging.getLogger("app.chat")
# The one logger that carries message text, kept separate so it can be filtered on its own.
transcript = logging.getLogger("app.transcript")

router = APIRouter()

# The fixed opening is bot message 1, so the 8th bot message is the warm close.
MAX_BOT_TURNS = 8
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _text(chunk) -> str:
    content = chunk.content
    if isinstance(content, str):
        return content
    return "".join(
        part if isinstance(part, str) else part.get("text", "") for part in content
    )


def _log_transcript(branch: str, turn: int, user_text: str | None, bot_text: str) -> None:
    # %r keeps each exchange on one line even when the text has newlines.
    transcript.info(
        "transcript: branch=%s turn=%d user=%r bot=%r",
        branch,
        turn,
        user_text,
        bot_text,
    )


def _static(text: str) -> StreamingResponse:
    """A fixed reply, streamed like a model reply so the client reads it the same way."""
    return StreamingResponse(
        iter([text]),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS,
    )


async def _route(req: ChatRequest) -> Branch:
    """Pick the conversation branch for the latest reply; 'mixed' if routing fails."""
    started = time.perf_counter()
    try:
        verdict = await get_router_llm().ainvoke(
            [
                SystemMessage(content=ROUTER_SYSTEM_PROMPT),
                HumanMessage(content=build_router_input(req.post, req.history)),
            ]
        )
    except Exception as exc:
        logger.warning(
            "chat: router failed, using mixed after %.2fs: %s",
            time.perf_counter() - started,
            describe_error(exc),
        )
        logger.debug("chat: traceback", exc_info=True)
        return "mixed"
    if not isinstance(verdict, RouteVerdict):
        logger.warning(
            "chat: router returned unexpected type=%s, using mixed",
            type(verdict).__name__,
        )
        return "mixed"
    logger.info(
        "chat: routed branch=%s latency=%.2fs",
        verdict.branch,
        time.perf_counter() - started,
    )
    return verdict.branch


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    settings = load_settings()
    if not settings.openrouter_api_key or not settings.chat_model:
        logger.warning(
            "chat: not configured (api_key=%s chat_model=%s)",
            bool(settings.openrouter_api_key),
            bool(settings.chat_model),
        )
        raise HTTPException(status_code=503, detail="Chat is not configured")

    if not req.history:
        _log_transcript("opening", 1, None, FIXED_OPENING)
        return _static(FIXED_OPENING)

    branch = await _route(req)

    model = settings.chat_model
    turns = len(req.history)
    bot_turn = sum(m.role == "ai" for m in req.history) + 1
    system = build_system_prompt(
        req.post, req.verdict, branch, closing=bot_turn >= MAX_BOT_TURNS
    )
    messages = [SystemMessage(content=system)]
    for m in req.history:
        cls = HumanMessage if m.role == "user" else AIMessage
        messages.append(cls(content=m.text))

    # Pull the first chunk before responding so a failure to start becomes a 502.
    # Apart from the transcript line at the end of the stream, only counts, timings and a
    # truncated error summary are logged, never user text.
    started = time.perf_counter()
    try:
        stream = get_chat_llm().astream(messages)
        first = await anext(stream, None)
    except Exception as exc:
        logger.error(
            "chat: failed to start model=%s history=%d after %.2fs: %s",
            model,
            turns,
            time.perf_counter() - started,
            describe_error(exc),
        )
        logger.debug("chat: traceback", exc_info=True)
        raise HTTPException(status_code=502, detail="Chat failed") from None

    logger.info(
        "chat: stream started model=%s history=%d first_chunk=%.2fs",
        model,
        turns,
        time.perf_counter() - started,
    )

    async def body():
        chunks = 0
        parts: list[str] = []
        if first is not None:
            chunks += 1
            text = _text(first)
            parts.append(text)
            yield text
        try:
            async for chunk in stream:
                chunks += 1
                text = _text(chunk)
                parts.append(text)
                yield text
        except Exception as exc:
            logger.error(
                "chat: stream failed model=%s after %d chunks, %.2fs: %s",
                model,
                chunks,
                time.perf_counter() - started,
                describe_error(exc),
            )
            logger.debug("chat: traceback", exc_info=True)
            # Headers are already sent; abort so the client sees a broken stream.
            raise RuntimeError("chat stream failed") from None
        logger.info(
            "chat: stream done model=%s chunks=%d total=%.2fs",
            model,
            chunks,
            time.perf_counter() - started,
        )
        _log_transcript(branch, bot_turn, req.history[-1].text, "".join(parts))

    return StreamingResponse(
        body(),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS,
    )
