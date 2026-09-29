import logging
import time

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import load_settings
from app.llm import get_classifier_llm
from app.logging_config import describe_error
from app.prompts.classifier import CLASSIFIER_SYSTEM_PROMPT
from app.schemas import ClassifyRequest, Verdict

logger = logging.getLogger("app.classify")

router = APIRouter()


@router.post("/classify", response_model=Verdict)
async def classify(req: ClassifyRequest) -> Verdict:
    settings = load_settings()
    if not settings.openrouter_api_key or not settings.classifier_model:
        logger.warning(
            "classify: not configured (api_key=%s classifier_model=%s)",
            bool(settings.openrouter_api_key),
            bool(settings.classifier_model),
        )
        raise HTTPException(status_code=503, detail="Classifier is not configured")

    model = settings.classifier_model
    messages = [
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=f"<post>\n{req.text}\n</post>"),
    ]
    # Fail closed: any LLM or parse failure is an error, never a "safe" verdict.
    # Only lengths and a truncated error summary are logged, never the post text.
    started = time.perf_counter()
    try:
        verdict = await get_classifier_llm().ainvoke(messages)
    except Exception as exc:
        logger.error(
            "classify: LLM call failed model=%s chars=%d after %.2fs: %s",
            model,
            len(req.text),
            time.perf_counter() - started,
            describe_error(exc),
        )
        logger.debug("classify: traceback", exc_info=True)
        raise HTTPException(status_code=502, detail="Classification failed") from None

    if not isinstance(verdict, Verdict):
        logger.error(
            "classify: unexpected result type=%s model=%s chars=%d",
            type(verdict).__name__,
            model,
            len(req.text),
        )
        raise HTTPException(status_code=502, detail="Classification failed")

    logger.info(
        "classify: ok model=%s chars=%d harmful=%s category=%s severity=%s latency=%.2fs",
        model,
        len(req.text),
        verdict.harmful,
        verdict.category,
        verdict.severity,
        time.perf_counter() - started,
    )
    return verdict
