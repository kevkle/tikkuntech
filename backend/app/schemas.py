from typing import Literal

from pydantic import BaseModel, Field, model_validator

Category = Literal["none", "self_harm", "violence", "harassment", "hate", "other"]
Severity = Literal["low", "medium", "high"]
Branch = Literal["default", "disengage"]
Language = Literal["en", "ar", "fr", "de"]


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
    language: Language | None = Field(
        default=None,
        description=(
            "Language the post is written in when it is en, ar, fr or de; null when it is "
            "any other language or cannot be told."
        ),
    )


class RouteVerdict(BaseModel):
    """Which conversation branch the user's latest reply belongs to."""

    branch: Branch = Field(
        description="Best-fitting branch for the user's latest reply."
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
    # What to call the person; the chat uses it like a human would. Optional.
    user_name: str | None = Field(default=None, max_length=50)
    # The language the person picked in the UI; the chat replies in it.
    language: Language = "en"

    @model_validator(mode="after")
    def history_ends_with_user(self) -> "ChatRequest":
        if self.history and self.history[-1].role != "user":
            raise ValueError("history must end with a user message")
        return self
