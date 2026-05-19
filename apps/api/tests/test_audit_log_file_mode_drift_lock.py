"""MH-DRIFTLOCK-AUDIT-LOG-FILE-MODE-PIN

Pins that the audit-log writer opens its file in append-only mode (``"a"``).
A switch to ``"w"`` would silently truncate the durable audit trail on every
process start.
"""
from __future__ import annotations

import inspect
from pathlib import Path

from app.services import audit_log_service


def _service_source() -> str:
    return inspect.getsource(audit_log_service)


def test_audit_log_uses_append_mode() -> None:
    src = _service_source()
    # Must contain the append-mode write call.
    assert '_AUDIT_LOG_PATH.open("a"' in src, (
        "Audit log writer must open the path in append mode ('a'). "
        "A switch to 'w' would truncate the durable audit trail."
    )
    # Must NOT contain a write-mode open of the audit path.
    assert '_AUDIT_LOG_PATH.open("w"' not in src, (
        "Audit log writer found in write/truncate mode ('w'). REJECT."
    )


def test_audit_log_path_default_pin() -> None:
    # Default path remains 'logs/audit.jsonl' (env override allowed).
    assert audit_log_service._AUDIT_LOG_PATH == Path("logs/audit.jsonl") or str(
        audit_log_service._AUDIT_LOG_PATH
    ).endswith("audit.jsonl"), (
        f"Audit log default path drifted: {audit_log_service._AUDIT_LOG_PATH}"
    )


def test_audit_log_parent_dir_mkdir_present() -> None:
    src = _service_source()
    assert "_AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)" in src, (
        "Audit log writer must mkdir parent directory before opening the file."
    )
