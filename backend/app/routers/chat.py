from fastapi import APIRouter, HTTPException

from app.schemas import ChatRequest

router = APIRouter()


@router.post("/chat")
def chat(req: ChatRequest):
    raise HTTPException(status_code=501, detail="Not implemented (Phase 3)")
