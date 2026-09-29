from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import load_settings
from app.llm import get_classifier_llm
from app.prompts.classifier import CLASSIFIER_SYSTEM_PROMPT
from app.schemas import ClassifyRequest, Verdict

router = APIRouter()


@router.post("/classify", response_model=Verdict)
async def classify(req: ClassifyRequest) -> Verdict:
    settings = load_settings()
    if not settings.openrouter_api_key or not settings.classifier_model:
        raise HTTPException(status_code=503, detail="Classifier is not configured")

    messages = [
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=f"<post>\n{req.text}\n</post>"),
    ]
    # Fail closed: any LLM or parse failure is an error, never a "safe" verdict.
    # `from None` and no logging keep the post text out of server output.
    try:
        verdict = await get_classifier_llm().ainvoke(messages)
    except Exception:
        raise HTTPException(status_code=502, detail="Classification failed") from None

    if not isinstance(verdict, Verdict):
        raise HTTPException(status_code=502, detail="Classification failed")
    return verdict
