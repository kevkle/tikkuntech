from pathlib import Path
from typing import get_args

import pytest

from app.prompts import classifier, router, support_chat
from app.prompts.loader import PROMPTS_DIR, load_prompt
from app.prompts.support_chat import CONTEXT_TAG, EXAMPLES, Phase
from app.schemas import Branch

# Prompts live in plain files so they can be edited without touching Python.


def test_prompts_dir_is_the_prompts_package():
    assert PROMPTS_DIR == Path(support_chat.__file__).parent


def test_load_prompt_drops_trailing_newlines_only():
    text = load_prompt("chat/closing.md")
    assert not text.endswith("\n")
    assert text.startswith("This is your final message")


def test_load_prompt_fails_fast_on_a_missing_file():
    with pytest.raises(FileNotFoundError):
        load_prompt("chat/does-not-exist.md")


@pytest.mark.parametrize("branch", get_args(Branch))
def test_every_branch_has_its_own_file(branch):
    path = PROMPTS_DIR / "chat" / "branches" / f"{branch}.md"
    assert path.is_file()
    assert support_chat.BRANCH_ADDENDA[branch] == load_prompt(f"chat/branches/{branch}.md")


@pytest.mark.parametrize("phase", get_args(Phase))
def test_every_phase_has_a_stage_file_and_an_examples_file(phase):
    assert (PROMPTS_DIR / "chat" / "stages" / f"{phase}.md").is_file()
    assert (PROMPTS_DIR / "chat" / "examples" / f"{phase}.md").is_file()
    assert phase in EXAMPLES


@pytest.mark.parametrize(
    "rel",
    [
        "chat/base.md",
        "chat/closing.md",
        "chat/stages/listen.md",
        "chat/stages/return.md",
        "chat/stages/continue.md",
        "router.md",
        "classifier.md",
    ]
    + [f"chat/branches/{b}.md" for b in get_args(Branch)],
)
def test_prompt_files_are_not_empty(rel):
    assert load_prompt(rel).strip()


def test_module_constants_come_from_the_files():
    assert support_chat.SUPPORT_CHAT_SYSTEM_PROMPT == load_prompt("chat/base.md")
    assert support_chat.CLOSING_INSTRUCTION == load_prompt("chat/closing.md")
    assert support_chat.LISTEN_NOTE == load_prompt("chat/stages/listen.md")
    assert support_chat.RETURN_TO_POST_NOTE == load_prompt("chat/stages/return.md")
    assert support_chat.CONTINUE_NOTE == load_prompt("chat/stages/continue.md")
    assert router.ROUTER_SYSTEM_PROMPT == load_prompt("router.md")
    assert classifier.CLASSIFIER_SYSTEM_PROMPT == load_prompt("classifier.md")


def test_base_prompt_names_the_context_block_by_its_tag():
    assert f"<{CONTEXT_TAG}>" in load_prompt("chat/base.md")
