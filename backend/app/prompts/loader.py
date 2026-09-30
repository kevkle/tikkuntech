"""Read prompt text from the plain files next to this module."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent

# First line of a drafted translation that a native speaker has not reviewed yet. It is a
# marker for people and tests, so it never reaches the model.
REVIEW_MARKER = "<!-- needs-native-review -->"


def load_prompt(relative_path: str) -> str:
    """Return a prompt file's text without its trailing newline or review marker.

    A missing file raises at import time, so a broken prompt path fails at startup
    instead of on the first chat request.
    """
    text = (PROMPTS_DIR / relative_path).read_text(encoding="utf-8")
    if text.startswith(REVIEW_MARKER):
        text = text[len(REVIEW_MARKER) :].lstrip("\n")
    return text.rstrip("\n")


def localized_path(relative_path: str, language: str) -> str:
    """The language's copy of a prompt file, or the English copy when it has none.

    "chat/opening.md" in French is "chat/locales/fr/opening.md" if that file exists, and
    otherwise "chat/locales/en/opening.md".
    """
    folder, _, name = relative_path.rpartition("/")
    prefix = f"{folder}/locales" if folder else "locales"
    candidate = f"{prefix}/{language}/{name}"
    return candidate if (PROMPTS_DIR / candidate).is_file() else f"{prefix}/en/{name}"


def load_sections(relative_path: str) -> dict[str, str]:
    """Split a prompt file into its "## name" sections, keyed by name.

    Each section's text excludes its heading and trailing newlines. A duplicate heading
    or text before the first heading raises at import time, like a missing file.
    """
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in load_prompt(relative_path).splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            if name in sections:
                raise ValueError(f"{relative_path}: duplicate section {name!r}")
            current = sections[name] = []
        elif current is not None:
            current.append(line)
        elif line.strip():
            raise ValueError(f"{relative_path}: text before the first '## ' heading")
    return {name: "\n".join(lines).strip("\n") for name, lines in sections.items()}
