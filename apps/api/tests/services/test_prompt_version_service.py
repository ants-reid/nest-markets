"""QA-109: seed_prompt_versions() upserts rows and is idempotent."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


from app.db.enums import PromptRole
from app.db.models.prompt_version import PromptVersion
from app.services.prompt_version_service import (
    _infer_role,
    _infer_version,
    seed_prompt_versions,
)


# ---------------------------------------------------------------------------
# Helper inference unit tests
# ---------------------------------------------------------------------------


def test_infer_role_signal_engine():
    assert _infer_role("signal_engine_v1.md") == PromptRole.SIGNAL_ENGINE


def test_infer_role_catalyst_classifier():
    assert _infer_role("catalyst_classifier_v2.md") == PromptRole.CATALYST_CLASSIFIER


def test_infer_role_signal_input_template():
    # User template maps to SIGNAL_ENGINE role
    assert _infer_role("signal_input_template_v1.md") == PromptRole.SIGNAL_ENGINE


def test_infer_role_unknown_returns_none():
    assert _infer_role("unknown_file_v1.md") is None


def test_infer_version_extracts_tag():
    assert _infer_version("signal_engine_v3.md") == "v3"


def test_infer_version_defaults_to_v1():
    assert _infer_version("signal_engine.md") == "v1"


# ---------------------------------------------------------------------------
# QA-109: seed_prompt_versions integration against mocked session + FS
# ---------------------------------------------------------------------------


def _make_fake_path(name: str, content: str, is_file: bool = True):
    p = MagicMock()
    p.name = name
    p.stem = name.rsplit(".", 1)[0]
    p.suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    p.is_file.return_value = is_file
    p.read_text.return_value = content
    return p


def test_seed_prompt_versions_creates_new_rows(tmp_path):
    """seed_prompt_versions should add a PromptVersion row for each prompt file."""
    # Create real temp prompt dirs
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "signal_engine_v1.md").write_text("You are a signal engine.", encoding="utf-8")

    user_dir = tmp_path / "user"
    user_dir.mkdir()
    (user_dir / "signal_input_template_v1.md").write_text("Analyse {{ticker}}.", encoding="utf-8")

    session = MagicMock()
    # scalar_one_or_none returns None → create branch
    session.execute.return_value.scalar_one_or_none.return_value = None

    with patch("app.services.prompt_version_service._PROMPTS_ROOT", tmp_path):
        count = seed_prompt_versions(session)

    assert count == 2
    assert session.add.call_count == 2
    session.flush.assert_called_once()


def test_seed_prompt_versions_idempotent_no_change(tmp_path):
    """If hash matches existing row, no update is counted."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    content = "You are a signal engine."
    (system_dir / "signal_engine_v1.md").write_text(content, encoding="utf-8")

    # Build a fake existing row with matching hash
    from app.services.prompt_version_service import _file_hash
    existing = MagicMock(spec=PromptVersion)
    existing.schema_json = {"hash": _file_hash(content)}

    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = existing

    with patch("app.services.prompt_version_service._PROMPTS_ROOT", tmp_path):
        count = seed_prompt_versions(session)

    # No rows added/updated
    assert count == 0
    session.add.assert_not_called()


def test_seed_prompt_versions_updates_on_hash_change(tmp_path):
    """If hash differs, row content should be updated and count incremented."""
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "signal_engine_v1.md").write_text("New content here.", encoding="utf-8")

    existing = MagicMock(spec=PromptVersion)
    existing.schema_json = {"hash": "old_hash_value_00"}

    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = existing

    with patch("app.services.prompt_version_service._PROMPTS_ROOT", tmp_path):
        count = seed_prompt_versions(session)

    assert count == 1
    # system_prompt updated on existing row
    assert existing.system_prompt == "New content here."
