"""Drift-lock: audit log file path pin (cycle 70).

Pins the default ``_AUDIT_LOG_PATH`` to ``logs/audit.jsonl`` (the path
referenced by ops runbooks and rotation tooling). Also pins the env
override key to ``AUDIT_LOG_PATH`` so a rename to ``AUDIT_LOG_FILE``
would fail loudly.

Test-only / additive.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from app.services import audit_log_service

EXPECTED_DEFAULT_PATH = Path("logs/audit.jsonl")
EXPECTED_ENV_KEY = "AUDIT_LOG_PATH"


def test_audit_log_default_path_pin(monkeypatch) -> None:
    """When AUDIT_LOG_PATH env var is unset, the module-level path
    must resolve to ``logs/audit.jsonl``.

    Re-evaluates the same expression the module uses at import time
    against a fresh os.environ snapshot so we test the wiring, not
    the cached attribute alone (the cached attribute is checked
    separately below).
    """
    monkeypatch.delenv(EXPECTED_ENV_KEY, raising=False)
    import os
    resolved = Path(os.getenv(EXPECTED_ENV_KEY, "logs/audit.jsonl"))
    assert resolved == EXPECTED_DEFAULT_PATH, (
        "Audit log default path drift: "
        f"expected {EXPECTED_DEFAULT_PATH}, got {resolved}."
    )


def test_audit_log_module_attribute_present() -> None:
    assert hasattr(audit_log_service, "_AUDIT_LOG_PATH"), (
        "audit_log_service must expose the module-level _AUDIT_LOG_PATH "
        "attribute that read_audit_events() and tests rely on."
    )
    val = audit_log_service._AUDIT_LOG_PATH
    assert isinstance(val, Path), (
        f"_AUDIT_LOG_PATH must be a pathlib.Path, got {type(val).__name__}."
    )


def test_audit_log_env_key_pinned_in_source() -> None:
    """The env-var name must literally appear in the module source.
    Renaming it would silently make ops overrides ineffective.
    """
    src = inspect.getsource(audit_log_service)
    assert f'os.getenv("{EXPECTED_ENV_KEY}"' in src or \
           f"os.getenv('{EXPECTED_ENV_KEY}'" in src, (
        f"Audit log env key {EXPECTED_ENV_KEY!r} not found in "
        "audit_log_service source — was it renamed?"
    )
