"""Tests for MH-159 — prompt registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.prompt_registry import (
    PromptRegistryError,
    describe_prompt_text,
    load_prompt_directory,
    load_prompt_file,
)


PROMPT_ROOT = Path(__file__).resolve().parents[1] / "app" / "prompts"


def test_parses_signal_engine_prompt():
    desc = load_prompt_file(PROMPT_ROOT / "system" / "signal_engine_v1.md")
    assert desc.name == "signal_engine"
    assert desc.role == "signal_engine"
    assert desc.version == "v1"
    assert desc.schema == "signal_schema_v1.json"
    assert desc.body.startswith("You are the Market Hunter signal engine.")
    assert len(desc.content_hash) == 64
    assert desc.version_id is not None


def test_version_id_is_stable():
    desc1 = load_prompt_file(PROMPT_ROOT / "system" / "signal_engine_v1.md")
    desc2 = load_prompt_file(PROMPT_ROOT / "system" / "signal_engine_v1.md")
    assert desc1.version_id == desc2.version_id
    assert desc1.content_hash == desc2.content_hash


def test_version_id_changes_when_body_changes():
    base = "# name: x\n# role: y\n# version: v1\n\nhello"
    other = "# name: x\n# role: y\n# version: v1\n\nhello world"
    a = describe_prompt_text(base)
    b = describe_prompt_text(other)
    assert a.content_hash != b.content_hash
    assert a.version_id != b.version_id


def test_version_id_changes_when_version_changes():
    a = describe_prompt_text("# name: x\n# role: y\n# version: v1\n\nbody")
    b = describe_prompt_text("# name: x\n# role: y\n# version: v2\n\nbody")
    assert a.content_hash == b.content_hash  # same body
    assert a.version_id != b.version_id


def test_missing_required_frontmatter_raises():
    with pytest.raises(PromptRegistryError):
        describe_prompt_text("# name: x\n# role: y\n\nbody")  # missing version
    with pytest.raises(PromptRegistryError):
        describe_prompt_text("plain body, no frontmatter at all")


def test_extra_frontmatter_is_captured():
    desc = describe_prompt_text(
        "# name: x\n# role: y\n# version: v1\n# author: alice\n\nbody"
    )
    assert desc.extra == {"author": "alice"}


def test_load_directory_skips_user_input_template():
    # The user/signal_input_template_v1.md has no frontmatter — should be skipped,
    # not error.
    descs = load_prompt_directory(PROMPT_ROOT)
    keys = set(descs.keys())
    assert "signal_engine/signal_engine@v1" in keys
    assert "catalyst_classifier/catalyst_classifier@v1" in keys


def test_load_directory_missing_root_raises(tmp_path):
    with pytest.raises(PromptRegistryError):
        load_prompt_directory(tmp_path / "does-not-exist")


def test_collision_detected(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("# name: x\n# role: y\n# version: v1\n\nbody A\n")
    b.write_text("# name: x\n# role: y\n# version: v1\n\nbody B different\n")
    with pytest.raises(PromptRegistryError):
        load_prompt_directory(tmp_path)


def test_identical_files_do_not_collide(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    text = "# name: x\n# role: y\n# version: v1\n\nbody\n"
    a.write_text(text)
    b.write_text(text)
    descs = load_prompt_directory(tmp_path)
    assert "y/x@v1" in descs


def test_body_excludes_frontmatter():
    desc = describe_prompt_text("# name: x\n# role: y\n# version: v1\n\nhello body")
    assert "name:" not in desc.body
    assert desc.body.startswith("hello body")
