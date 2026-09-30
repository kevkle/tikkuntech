import logging
import time

from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import load_settings
from app.llm import get_chat_llm, get_router_llm
from app.logging_config import describe_error
from app.prompts.router import ROUTER_SYSTEM_PROMPT, build_router_input
from app.prompts.support_chat import Phase, build_system_prompt, build_turn_guidance, opening_for
from app.schemas import Branch, ChatRequest, RouteVerdict

logger = logging.getLogger("app.chat")
# The one logger that carries message text, kept separate so it can be filtered on its own.
transcript = logging.getLogger("app.transcript")

router = APIRouter()

# The fixed opening is bot message 1, so the 8th bot message is the warm close.
MAX_BOT_TURNS = 8
# The return to the post (and the option buttons) happens when the router says the person
# is ready, from bot message MENU_MIN_TURN on, and at the latest on MENU_FALLBACK_TURN.
MENU_MIN_TURN = 3
MENU_FALLBACK_TURN = 6
FALLBACK_REASON = "fallback: router unavailable"
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _text(chunk) -> str:
    content = chunk.content
    if isinstance(content, str):
        return content
    return "".join(
        part if isinstance(part, str) else part.get("text", "") for part in content
    )


def _log_transcript(
    branch: str,
    reason: str | None,
    turn: int,
    user_text: str | None,
    bot_text: str,
    partial: bool = False,
) -> None:
    # %r keeps each exchange on one line even when the text has newlines. The router's
    # reason is model-written and can quote the person, so it lives here and nowhere else.
    # partial=True marks a reply that was cut off: the text is what had streamed so far.
    transcript.info(
        "transcript: branch=%s turn=%d reason=%r user=%r bot=%r%s",
        branch,
        turn,
        reason,
        user_text,
        bot_text,
        " partial=True" if partial else "",
    )


def _static(text: str) -> StreamingResponse:
    """A fixed reply, streamed like a model reply so the client reads it the same way."""
    return StreamingResponse(
        iter([text]),
        media_type="text/plain; charset=utf-8",
        headers=STREAM_HEADERS,
    )


ChatPhase = Phase


def _phase(
    branch: Branch,
    ready: bool,
    bot_turn: int,
    last_phase: Literal["return", "close"] | None,
) -> ChatPhase | None:
    """Where the conversation is: listening, returning to the post, closing with the
    options, or past the close."""
    if branch == "disengage":
        return None
    if last_phase == "close":
        return "continue"
    if last_phase == "return" or bot_turn >= MAX_BOT_TURNS:
        return "close"
    if bot_turn >= MENU_MIN_TURN and (ready or bot_turn >= MENU_FALLBACK_TURN):
        return "return"
    return "listen"


async def _route(req: ChatRequest) -> tuple[Branch, bool, str]:
    """Pick the branch, readiness and the router's reason; 'mixed', not ready if routing fails."""
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
        return "mixed", False, FALLBACK_REASON
    if not isinstance(verdict, RouteVerdict):
        logger.warning(
            "chat: router returned unexpected type=%s, using mixed",
            type(verdict).__name__,
        )
        return "mixed", False, FALLBACK_REASON
    logger.info(
        "chat: routed branch=%s ready=%s latency=%.2fs",
        verdict.branch,
        verdict.ready,
        time.perf_counter() - started,
    )
    return verdict.branch, verdict.ready, verdict.reason


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

    # The post's own language wins; the picker only decides when it is unknown.
    language = req.verdict.language or req.language
    if not req.history:
        opening = opening_for(language, req.user_name)
        _log_transcript("opening", None, 1, None, opening)
        return _static(opening)

    branch, ready, reason = await _route(req)
    bot_turn = sum(m.role == "ai" for m in req.history) + 1
    phase = _phase(branch, ready, bot_turn, req.last_phase)
    logger.info(
        "chat: phase=%s ready=%s turn=%d last_phase=%s",
        phase,
        ready,
        bot_turn,
        req.last_phase,
    )
    # The client echoes the stage back next turn, and shows the option buttons from the
    # close on, so they arrive with the message that introduces them.
    headers = dict(STREAM_HEADERS)
    if phase in ("return", "close"):
        headers["X-Chat-Phase"] = phase
    if phase in ("close", "continue"):
        headers["X-Chat-Menu"] = branch

    model = settings.chat_model
    turns = len(req.history)
    system = build_system_prompt(
        req.post,
        req.verdict,
        user_name=req.user_name,
        language=language,
    )
    guidance = build_turn_guidance(branch, phase)
    # The system prompt is one block that never changes within a conversation, marked so the
    # provider can cache it. The per-turn guidance rides on the last user message.
    messages = [
        SystemMessage(
            content=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        )
    ]
    last = len(req.history) - 1
    for i, m in enumerate(req.history):
        if m.role == "ai":
            messages.append(AIMessage(content=m.text))
        elif i == last:
            messages.append(
                HumanMessage(
                    content=[
                        {"type": "text", "text": m.text},
                        {"type": "text", "text": guidance},
                    ]
                )
            )
        else:
            messages.append(HumanMessage(content=m.text))

    # Pull the first chunk before responding so a failure to start becomes a 502.
    # Apart from the transcript line written when the stream ends (or is cut off), only
    # counts, timings and a truncated error summary are logged, never user text.
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
        finished = False
        try:
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
            finished = True
        finally:
            # Runs on success, an upstream failure, and a dropped connection alike, so a
            # reply the person only partly saw is still recorded, marked partial.
            _log_transcript(
                branch,
                reason,
                bot_turn,
                req.history[-1].text,
                "".join(parts),
                partial=not finished,
            )

    return StreamingResponse(
        body(),
        media_type="text/plain; charset=utf-8",
        headers=headers,
    )
