import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    openrouter_base_url: str
    classifier_model: str
    chat_model: str


def load_settings() -> Settings:
    return Settings(
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        openrouter_base_url=os.environ.get(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ),
        classifier_model=os.environ.get("CLASSIFIER_MODEL", ""),
        chat_model=os.environ.get("CHAT_MODEL", ""),
    )
