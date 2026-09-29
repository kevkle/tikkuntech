from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
    text: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    post: str = Field(min_length=1, max_length=2000)
    verdict: Verdict
    # Empty history means "write the opening message".
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def history_ends_with_user(self) -> "ChatRequest":
        if self.history and self.history[-1].role != "user":
            raise ValueError("history must end with a user message")
        return self
