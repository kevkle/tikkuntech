"""Read prompt text from the plain files next to this module."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(relative_path: str) -> str:
    """Return a prompt file's text without its trailing newline.

    A missing file raises at import time, so a broken prompt path fails at startup
    instead of on the first chat request.
    """
    return (PROMPTS_DIR / relative_path).read_text(encoding="utf-8").rstrip("\n")


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
