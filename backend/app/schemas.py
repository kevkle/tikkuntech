from typing import Literal

from pydantic import BaseModel


class ClassifyRequest(BaseModel):
    text: str


class Verdict(BaseModel):
    harmful: bool
    category: str
    severity: Literal["low", "medium", "high"]
    reason: str


class ChatMessage(BaseModel):
    role: Literal["user", "ai"]
    text: str


class ChatRequest(BaseModel):
    post: str
    verdict: Verdict
    history: list[ChatMessage] = []
