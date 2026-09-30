from typing import Literal

from pydantic import BaseModel, Field, model_validator

Category = Literal["none", "self_harm", "violence", "harassment", "hate", "other"]
Severity = Literal["low", "medium", "high"]
Branch = Literal["belief", "grievance", "joke", "mixed", "disengage"]


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


class RouteVerdict(BaseModel):
    """Which conversation branch the user's latest reply belongs to."""

    branch: Branch = Field(
        description="Best-fitting branch for the user's latest reply."
    )
    ready: bool = Field(
        description=(
            "True only when the person has said what is underneath the post, sounds "
            "steadier, and is not escalating or defending. False when unsure."
        )
    )
    reason: str = Field(description="One short sentence explaining the choice.")


class ChatMessage(BaseModel):
    role: Literal["user", "ai"]
    text: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    post: str = Field(min_length=1, max_length=2000)
    verdict: Verdict
    # Empty history means "send the fixed opening message".
    history: list[ChatMessage] = Field(default_factory=list, max_length=40)
    # The stage of the last bot message, echoed from the X-Chat-Phase header: after
    # "return" the next reply is the close, after "close" the chat continues. The server
    # itself keeps no conversation state.
    last_phase: Literal["return", "close"] | None = None
    # What to call the person; the chat uses it like a human would. Optional.
    user_name: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def history_ends_with_user(self) -> "ChatRequest":
        if self.history and self.history[-1].role != "user":
            raise ValueError("history must end with a user message")
        return self
