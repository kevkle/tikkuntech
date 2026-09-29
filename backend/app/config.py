import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    classifier_model: str
    chat_model: str


def load_settings() -> Settings:
    return Settings(
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        classifier_model=os.environ.get("CLASSIFIER_MODEL", ""),
        chat_model=os.environ.get("CHAT_MODEL", ""),
    )
