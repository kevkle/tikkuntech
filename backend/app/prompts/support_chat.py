from typing import Literal, get_args

from app.prompts.loader import load_prompt, load_sections
from app.schemas import Branch, Verdict

CONTEXT_TAG = "flagged_post_context"

# The first message is fixed, so no model call is needed to start the chat.
FIXED_OPENING = "What made you say that?"

# The prompt text lives in plain files under chat/ so it can be edited without touching
# Python: base.md, branches.md, stages.md, examples.md and closing.md. The last three
# split into one "## name" section per branch or phase.
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
_EXAMPLE_SECTIONS = load_sections("chat/examples.md")
EXAMPLES: dict[Phase, str] = {phase: _EXAMPLE_SECTIONS[phase] for phase in get_args(Phase)}


def stage_note(phase: Phase | None) -> str | None:
    """Stage guidance for the phase, or None when there is no phase."""
    return _NOTES.get(phase) if phase else None


CLOSING_INSTRUCTION = load_prompt("chat/closing.md")


def build_system_prompt(
    post: str,
    verdict: Verdict,
    branch: Branch = "mixed",
    closing: bool = False,
    phase: Phase | None = None,
) -> str:
    # Strip the closing tag from user text so a post cannot break out of the block.
    safe_post = post.replace(f"</{CONTEXT_TAG}>", "")
    sections = [SUPPORT_CHAT_SYSTEM_PROMPT, BRANCH_ADDENDA[branch]]
    # The close and the disengage branch have their own instructions, so no stage note.
    note = None if closing or branch == "disengage" else stage_note(phase)
    if note:
        sections.append(note)
        examples = EXAMPLES.get(phase)
        if examples:
            sections.append(examples)
    if closing:
        sections.append(CLOSING_INSTRUCTION)
    return (
        "\n\n".join(sections)
        + "\n\n"
        + f"<{CONTEXT_TAG}>\n"
        + f"Draft post:\n{safe_post}\n\n"
        + f"Category: {verdict.category}\n"
        + f"Severity: {verdict.severity}\n"
        + f"Reason: {verdict.reason}\n"
        + f"</{CONTEXT_TAG}>"
    )
