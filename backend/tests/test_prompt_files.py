from pathlib import Path
from typing import get_args

import pytest

from app.prompts import classifier, router, support_chat
from app.prompts.loader import PROMPTS_DIR, load_prompt, load_sections, localized_path
from app.prompts.support_chat import (
    CONTEXT_TAG,
    EXAMPLES,
    EXAMPLES_BY_LANGUAGE,
    FIXED_OPENING,
    OPENINGS,
    Phase,
)
from app.schemas import Branch, Language

# Prompts live in plain files so they can be edited without touching Python.


def test_prompts_dir_is_the_prompts_package():
    assert PROMPTS_DIR == Path(support_chat.__file__).parent


def test_load_prompt_drops_trailing_newlines_only():
    text = load_prompt("chat/base.md")
    assert not text.endswith("\n")
    assert text.startswith("You are an AI chat assistant")


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


def make_locale_tree(tmp_path, monkeypatch):
    (tmp_path / "chat" / "locales" / "fr").mkdir(parents=True)
    (tmp_path / "chat" / "locales" / "en").mkdir(parents=True)
    (tmp_path / "chat" / "locales" / "en" / "opening.md").write_text("english\n")
    (tmp_path / "chat" / "locales" / "fr" / "opening.md").write_text("francais\n")
    monkeypatch.setattr("app.prompts.loader.PROMPTS_DIR", tmp_path)


def test_localized_path_prefers_the_language_file(tmp_path, monkeypatch):
    make_locale_tree(tmp_path, monkeypatch)
    assert localized_path("chat/opening.md", "fr") == "chat/locales/fr/opening.md"


def test_localized_path_falls_back_to_the_english_file(tmp_path, monkeypatch):
    make_locale_tree(tmp_path, monkeypatch)
    assert localized_path("chat/opening.md", "de") == "chat/locales/en/opening.md"


def test_localized_path_for_english_is_the_english_locale_file(tmp_path, monkeypatch):
    make_locale_tree(tmp_path, monkeypatch)
    assert localized_path("chat/opening.md", "en") == "chat/locales/en/opening.md"


def test_load_prompt_drops_the_needs_review_marker(tmp_path, monkeypatch):
    (tmp_path / "p.md").write_text("<!-- needs-native-review -->\nbonjour\n")
    monkeypatch.setattr("app.prompts.loader.PROMPTS_DIR", tmp_path)
    assert load_prompt("p.md") == "bonjour"


def test_load_sections_ignores_the_needs_review_marker(tmp_path, monkeypatch):
    (tmp_path / "s.md").write_text("<!-- needs-native-review -->\n## a\n\nx\n")
    monkeypatch.setattr("app.prompts.loader.PROMPTS_DIR", tmp_path)
    assert load_sections("s.md") == {"a": "x"}


# Drafted locale files live under chat/locales/<language>/. There are none until they are
# written, in which case the parametrized tests below are skipped.
LOCALE_FILES = sorted((PROMPTS_DIR / "chat" / "locales").glob("*/*.md"))
SECTIONED = {"examples.md"}


def test_locale_folders_are_supported_languages():
    assert {p.parent.name for p in LOCALE_FILES} <= set(get_args(Language))


@pytest.mark.parametrize("path", LOCALE_FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_locale_files_mirror_an_english_file(path):
    rel = path.relative_to(PROMPTS_DIR).as_posix()
    english = f"chat/locales/en/{path.name}"
    assert (PROMPTS_DIR / english).exists()
    assert load_prompt(rel).strip()
    if path.name in SECTIONED:
        assert set(load_sections(rel)) == set(load_sections(english))


def test_opening_is_a_prompt_file():
    assert FIXED_OPENING == load_prompt("chat/locales/en/opening.md")
    assert OPENINGS["en"] == FIXED_OPENING


@pytest.mark.parametrize("language", get_args(Language))
def test_every_language_has_an_opening_and_examples(language):
    assert OPENINGS[language].strip()
    assert all(EXAMPLES_BY_LANGUAGE[language][phase] for phase in get_args(Phase))


def test_english_examples_are_the_examples_constant():
    assert EXAMPLES_BY_LANGUAGE["en"] is EXAMPLES


def test_branches_file_has_one_section_per_branch():
    sections = load_sections("chat/branches.md")
    assert set(sections) == set(get_args(Branch))
    for branch in get_args(Branch):
        assert support_chat.BRANCH_ADDENDA[branch] == sections[branch]


@pytest.mark.parametrize("rel", ["chat/stages.md", "chat/locales/en/examples.md"])
def test_phase_files_have_one_section_per_phase(rel):
    assert set(load_sections(rel)) == set(get_args(Phase))


def test_every_phase_has_examples():
    assert all(EXAMPLES[phase] for phase in get_args(Phase))


@pytest.mark.parametrize(
    "rel",
    [
        "chat/base.md",
        "chat/reply_language.md",
        "chat/selection.md",
        "chat/locales/en/opening.md",
        "chat/branches.md",
        "chat/stages.md",
        "chat/locales/en/examples.md",
        "router.md",
        "classifier.md",
    ],
)
def test_prompt_files_are_not_empty(rel):
    assert load_prompt(rel).strip()


@pytest.mark.parametrize(
    "rel", ["chat/branches.md", "chat/stages.md", "chat/locales/en/examples.md"]
)
def test_no_section_is_empty(rel):
    assert all(text.strip() for text in load_sections(rel).values())


def test_module_constants_come_from_the_files():
    assert support_chat.SUPPORT_CHAT_SYSTEM_PROMPT == load_prompt("chat/base.md")
    assert support_chat.SELECTION_NOTE == load_prompt("chat/selection.md")
    stages = load_sections("chat/stages.md")
    assert support_chat.REFLECT_NOTE == stages["reflect"]
    assert support_chat.CLOSE_NOTE == stages["close"]
    assert router.ROUTER_SYSTEM_PROMPT == load_prompt("router.md")
    assert classifier.CLASSIFIER_SYSTEM_PROMPT == load_prompt("classifier.md")


def test_base_prompt_names_the_context_block_by_its_tag():
    assert f"<{CONTEXT_TAG}>" in load_prompt("chat/base.md")


def test_reply_language_file_has_the_language_placeholder():
    assert "{language}" in load_prompt("chat/reply_language.md")


@pytest.mark.parametrize("language", get_args(Language))
def test_no_locale_folder_carries_instructions(language):
    names = {p.name for p in (PROMPTS_DIR / "chat" / "locales" / language).glob("*.md")}
    expected = {"opening.md", "opening_named.md"}
    # Only English has examples; the other languages fall back to them.
    assert names == (expected | {"examples.md"} if language == "en" else expected)


import re

EXPECTED_EXAMPLE_COUNTS = {"reflect": 4, "close": 4}


def _examples_text(language):
    return load_sections(f"chat/locales/{language}/examples.md")


def _replies(section):
    return re.findall(r"<reply>(.*?)</reply>", _examples_text("en")[section], flags=re.S)


def test_english_example_counts_per_section():
    sections = _examples_text("en")
    assert {n: t.count("<example>") for n, t in sections.items()} == EXPECTED_EXAMPLE_COUNTS


@pytest.mark.parametrize("language", ["ar", "de", "fr"])
def test_other_languages_use_the_english_examples(language):
    assert not (PROMPTS_DIR / "chat" / "locales" / language / "examples.md").exists()
    assert EXAMPLES_BY_LANGUAGE[language] == EXAMPLES


CLOSING_QUESTION = "What would you like to do with your post?"


def test_reflect_example_replies_have_no_question():
    replies = _replies("reflect")
    assert len(replies) == EXPECTED_EXAMPLE_COUNTS["reflect"]
    assert not [r for r in replies if "?" in r]


def test_close_example_replies_end_with_the_closing_question_and_no_other():
    replies = _replies("close")
    assert len(replies) == EXPECTED_EXAMPLE_COUNTS["close"]
    for reply in replies:
        assert reply.strip().endswith(CLOSING_QUESTION)
        assert reply.count("?") == 1


@pytest.mark.parametrize("section,limit", [("reflect", 2), ("close", 3)])
def test_example_replies_stay_within_the_sentence_limit(section, limit):
    for reply in _replies(section):
        assert len(re.findall(r"[.!?](?:\s|$)", reply.strip())) <= limit


def test_close_examples_do_not_list_the_options():
    text = _examples_text("en")["close"]
    for option in ("1. Edit it", "2. Save it for later", "3. Delete it", "4. Post it"):
        assert option not in text


def test_close_examples_start_from_the_reflect_reply():
    section = _examples_text("en")["close"]
    assert section.count("<earlier>") == section.count("<example>")
    reflect_replies = _replies("reflect")
    earlier = re.findall(r"<earlier>Assistant: (.*?)</earlier>", section, flags=re.S)
    assert earlier == reflect_replies


def test_reflect_examples_start_from_the_opening_question():
    section = _examples_text("en")["reflect"]
    assert section.count("<earlier>Assistant: What made you want to post this right now?</earlier>") == 4
