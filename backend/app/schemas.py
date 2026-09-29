from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["none", "self_harm", "violence", "harassment", "hate", "other"]
Severity = Literal["low", "medium", "high"]


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class Verdict(BaseModel):
    """Harm classification of a draft social-media post."""

    harmful: bool = Field(description="True if the post is harmful in any category.")
    category: Category = Field(
        description="Best-fitting harm category, or 'none' if the post is not harmful."
    )
    severity: Severity = Field(
        description="Severity of the harm. Use 'low' when the post is not harmful."
    )
    reason: str = Field(description="One short sentence explaining the verdict.")


class ChatMessage(BaseModel):
    role: Literal["user", "ai"]
    text: str


class ChatRequest(BaseModel):
    post: str
    verdict: Verdict
    history: list[ChatMessage] = []
