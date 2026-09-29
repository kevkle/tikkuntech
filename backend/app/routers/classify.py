from fastapi import APIRouter, HTTPException

from app.schemas import ClassifyRequest, Verdict

router = APIRouter()


@router.post("/classify", response_model=Verdict)
def classify(req: ClassifyRequest) -> Verdict:
    raise HTTPException(status_code=501, detail="Not implemented (Phase 2)")
