from typing import Literal, get_args

from app.prompts.loader import load_prompt, load_sections, localized_path
from app.schemas import Branch, Language, Verdict

CONTEXT_TAG = "flagged_post_context"

# The prompt text lives in plain files under chat/ so it can be edited without touching
# Python: base.md, branches.md, stages.md, examples.md, closing.md and opening.md. The
# branches, stages and examples files split into one "## name" section per branch or phase.
# The opening, examples and closing are also written per language under
# chat/locales/<language>/, and the English file stands in for any that are missing.
LANGUAGES: tuple[Language, ...] = get_args(Language)
LANGUAGE_NAMES: dict[Language, str] = {
    "en": "English",
    "ar": "Arabic",
    "fr": "French",
    "de": "German",
}

# The first message is fixed, so no model call is needed to start the chat.
OPENINGS: dict[Language, str] = {
    language: load_prompt(localized_path("chat/opening.md", language)) for language in LANGUAGES
}
FIXED_OPENING = OPENINGS["en"]

# The same opening with "{name}" in it, used when the person's name is known.
OPENINGS_NAMED: dict[Language, str] = {
    language: load_prompt(localized_path("chat/opening_named.md", language))
    for language in LANGUAGES
}
NAME_PLACEHOLDER = "{name}"


def _clean_name(user_name: str | None) -> str:
    """The name on one line, without the context closing tag, or "" when there is none."""
    return " ".join((user_name or "").replace(f"</{CONTEXT_TAG}>", "").split())


def opening_for(language: Language, user_name: str | None = None) -> str:
    name = _clean_name(user_name)
    if not name:
        return OPENINGS[language]
    return OPENINGS_NAMED[language].replace(NAME_PLACEHOLDER, name)


SUPPORT_CHAT_SYSTEM_PROMPT = load_prompt("chat/base.md")

# One addendum per branch. "mixed" is also the default when the router cannot decide.
_BRANCH_SECTIONS = load_sections("chat/branches.md")
BRANCH_ADDENDA: dict[Branch, str] = {branch: _BRANCH_SECTIONS[branch] for branch in get_args(Branch)}

# Stage guidance, chosen by the conversation phase the server works out each turn.
Phase = Literal["listen", "return", "continue"]

_STAGE_SECTIONS = load_sections("chat/stages.md")
LISTEN_NOTE = _STAGE_SECTIONS["listen"]
RETURN_TO_POST_NOTE = _STAGE_SECTIONS["return"]
CONTINUE_NOTE = _STAGE_SECTIONS["continue"]

_NOTES: dict[Phase, str] = {
    "listen": LISTEN_NOTE,
    "return": RETURN_TO_POST_NOTE,
    "continue": CONTINUE_NOTE,
}

# Worked examples for each phase, appended after its stage note (empty section = none).
def _examples(language: Language) -> dict[Phase, str]:
    sections = load_sections(localized_path("chat/examples.md", language))
    return {phase: sections[phase] for phase in get_args(Phase)}


EXAMPLES: dict[Phase, str] = _examples("en")
EXAMPLES_BY_LANGUAGE: dict[Language, dict[Phase, str]] = {
    language: EXAMPLES if language == "en" else _examples(language) for language in LANGUAGES
}


def stage_note(phase: Phase | None) -> str | None:
    """Stage guidance for the phase, or None when there is no phase."""
    return _NOTES.get(phase) if phase else None


CLOSINGS: dict[Language, str] = {
    language: load_prompt(localized_path("chat/closing.md", language)) for language in LANGUAGES
}
CLOSING_INSTRUCTION = CLOSINGS["en"]


def reply_language_note(language: Language) -> str:
    return (
        "Reply in the language the person wrote their latest message in, idiomatic as a "
        "native speaker would write it and in that language's own script. If it is unclear, "
        f"or they haven't written yet, reply in {LANGUAGE_NAMES[language]}. "
        "The rules above apply unchanged."
    )


def build_system_prompt(
    post: str,
    verdict: Verdict,
    branch: Branch = "mixed",
    closing: bool = False,
    phase: Phase | None = None,
    user_name: str | None = None,
    language: Language = "en",
) -> str:
    # Strip the closing tag from user text so a post cannot break out of the block.
    safe_post = post.replace(f"</{CONTEXT_TAG}>", "")
    # The name goes on one line, so collapse any newlines and drop the closing tag too.
    safe_name = _clean_name(user_name)
    name_line = f"Person's name: {safe_name}\n" if safe_name else ""
    sections = [
        SUPPORT_CHAT_SYSTEM_PROMPT,
        reply_language_note(language),
        BRANCH_ADDENDA[branch],
    ]
    # The close and the disengage branch have their own instructions, so no stage note.
    note = None if closing or branch == "disengage" else stage_note(phase)
    if note:
        sections.append(note)
        examples = EXAMPLES_BY_LANGUAGE[language].get(phase)
        if examples:
            sections.append(examples)
    if closing:
        sections.append(CLOSINGS[language])
    return (
        "\n\n".join(sections)
        + "\n\n"
        + f"<{CONTEXT_TAG}>\n"
        + name_line
        + f"Draft post:\n{safe_post}\n\n"
        + f"Category: {verdict.category}\n"
        + f"Severity: {verdict.severity}\n"
        + f"Reason: {verdict.reason}\n"
        + f"</{CONTEXT_TAG}>"
    )
