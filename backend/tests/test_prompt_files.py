from pathlib import Path
from typing import get_args

import pytest

from app.prompts import classifier, router, support_chat
from app.prompts.loader import PROMPTS_DIR, load_prompt, load_sections
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


def test_load_sections_splits_on_headings(tmp_path, monkeypatch):
    (tmp_path / "s.md").write_text("## a\n\nfirst\nline\n\n## b\n\nsecond\n")
    monkeypatch.setattr("app.prompts.loader.PROMPTS_DIR", tmp_path)
    assert load_sections("s.md") == {"a": "first\nline", "b": "second"}


def test_load_sections_rejects_a_duplicate_heading(tmp_path, monkeypatch):
    (tmp_path / "s.md").write_text("## a\n\nx\n\n## a\n\ny\n")
    monkeypatch.setattr("app.prompts.loader.PROMPTS_DIR", tmp_path)
    with pytest.raises(ValueError, match="duplicate"):
        load_sections("s.md")


def test_load_sections_rejects_text_before_the_first_heading(tmp_path, monkeypatch):
    (tmp_path / "s.md").write_text("stray\n\n## a\n\nx\n")
    monkeypatch.setattr("app.prompts.loader.PROMPTS_DIR", tmp_path)
    with pytest.raises(ValueError, match="before the first"):
        load_sections("s.md")


def test_branches_file_has_one_section_per_branch():
    sections = load_sections("chat/branches.md")
    assert set(sections) == set(get_args(Branch))
    for branch in get_args(Branch):
        assert support_chat.BRANCH_ADDENDA[branch] == sections[branch]


@pytest.mark.parametrize("file", ["stages", "examples"])
def test_phase_files_have_one_section_per_phase(file):
    assert set(load_sections(f"chat/{file}.md")) == set(get_args(Phase))


def test_every_phase_has_examples():
    assert all(EXAMPLES[phase] for phase in get_args(Phase))


@pytest.mark.parametrize(
    "rel",
    [
        "chat/base.md",
        "chat/closing.md",
        "chat/branches.md",
        "chat/stages.md",
        "chat/examples.md",
        "router.md",
        "classifier.md",
    ],
)
def test_prompt_files_are_not_empty(rel):
    assert load_prompt(rel).strip()


@pytest.mark.parametrize("file", ["branches", "stages", "examples"])
def test_no_section_is_empty(file):
    assert all(text.strip() for text in load_sections(f"chat/{file}.md").values())


def test_module_constants_come_from_the_files():
    assert support_chat.SUPPORT_CHAT_SYSTEM_PROMPT == load_prompt("chat/base.md")
    assert support_chat.CLOSING_INSTRUCTION == load_prompt("chat/closing.md")
    stages = load_sections("chat/stages.md")
    assert support_chat.LISTEN_NOTE == stages["listen"]
    assert support_chat.RETURN_TO_POST_NOTE == stages["return"]
    assert support_chat.CONTINUE_NOTE == stages["continue"]
    assert router.ROUTER_SYSTEM_PROMPT == load_prompt("router.md")
    assert classifier.CLASSIFIER_SYSTEM_PROMPT == load_prompt("classifier.md")


def test_base_prompt_names_the_context_block_by_its_tag():
    assert f"<{CONTEXT_TAG}>" in load_prompt("chat/base.md")
