"""Read prompt text from the plain files next to this module."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(relative_path: str) -> str:
    """Return a prompt file's text without its trailing newline.

    A missing file raises at import time, so a broken prompt path fails at startup
    instead of on the first chat request.
    """
    return (PROMPTS_DIR / relative_path).read_text(encoding="utf-8").rstrip("\n")
