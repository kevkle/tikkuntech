from typing import Literal, get_args

from app.prompts.loader import load_prompt, load_sections, localized_path
from app.schemas import Branch, Language, Verdict

CONTEXT_TAG = "flagged_post_context"

# The prompt text lives in plain files under chat/ so it can be edited without touching
# Python: base.md, branches.md, stages.md, reply_language.md and selection.md, which are
# shared by every language. The branches, stages and examples files split into one "## name"
# section per branch or phase. Only the opening and the examples are written per language
# under chat/locales/<language>/, and the English file stands in for any that are missing
# (today only English examples exist).
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
SELECTION_NOTE = load_prompt("chat/selection.md")
REPLY_LANGUAGE_NOTE = load_prompt("chat/reply_language.md")

# One addendum per branch. "default" is also used when the router cannot decide.
_BRANCH_SECTIONS = load_sections("chat/branches.md")
BRANCH_ADDENDA: dict[Branch, str] = {branch: _BRANCH_SECTIONS[branch] for branch in get_args(Branch)}

# Stage guidance, chosen each turn by the conversation phase the server works out.
Phase = Literal["reflect", "close"]

_STAGE_SECTIONS = load_sections("chat/stages.md")
STAGE_NOTES: dict[Phase, str] = {phase: _STAGE_SECTIONS[phase] for phase in get_args(Phase)}
REFLECT_NOTE = STAGE_NOTES["reflect"]
CLOSE_NOTE = STAGE_NOTES["close"]


# Worked examples for each phase, per language.
def _examples(language: Language) -> dict[Phase, str]:
    sections = load_sections(localized_path("chat/examples.md", language))
    return {phase: sections[phase] for phase in get_args(Phase)}


EXAMPLES: dict[Phase, str] = _examples("en")
EXAMPLES_BY_LANGUAGE: dict[Language, dict[Phase, str]] = {
    language: EXAMPLES if language == "en" else _examples(language) for language in LANGUAGES
}


def reply_language_note(language: Language) -> str:
    return REPLY_LANGUAGE_NOTE.replace("{language}", LANGUAGE_NAMES[language])


def _tagged(tag: str, name: str, body: str) -> str:
    return f'<{tag} name="{name}">\n{body}\n</{tag}>'


def build_system_prompt(
    post: str,
    verdict: Verdict,
    user_name: str | None = None,
    language: Language = "en",
) -> str:
    """The prompt that stays the same for a whole conversation, so it can be cached."""
    # Strip the closing tag from user text so a post cannot break out of the block.
    safe_post = post.replace(f"</{CONTEXT_TAG}>", "")
    # The name goes on one line, so collapse any newlines and drop the closing tag too.
    safe_name = _clean_name(user_name)
    name_line = f"Person's name: {safe_name}\n" if safe_name else ""
    branches = "\n\n".join(_tagged("branch", b, BRANCH_ADDENDA[b]) for b in get_args(Branch))
    stages = "\n\n".join(_tagged("stage", p, STAGE_NOTES[p]) for p in get_args(Phase))
    examples = "\n\n".join(
        _tagged("stage_examples", p, EXAMPLES_BY_LANGUAGE[language][p]) for p in get_args(Phase)
    )
    sections = [
        SUPPORT_CHAT_SYSTEM_PROMPT,
        reply_language_note(language),
        SELECTION_NOTE,
        f"<branches>\n{branches}\n</branches>",
        f"<stages>\n{stages}\n</stages>",
        examples,
    ]
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


def build_turn_guidance(branch: Branch, phase: Phase | None) -> str:
    """The few lines that change every turn: which branch and stage are active."""
    stage = f"Active stage: {phase}" if phase else "No stage applies on this turn."
    return f"<turn_guidance>\nActive branch: {branch}\n{stage}\n</turn_guidance>"
