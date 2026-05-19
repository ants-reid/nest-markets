"""MH-DRIFTLOCK-AUDIT-LOG-FILE-PATH-MODULE-CONST-PIN

Pins that ``audit_log_service._AUDIT_LOG_PATH`` exists, is a ``Path``,
and points to a file named ``audit.log``. Silent redirection of the
audit-trail target would defeat every other audit-log pin.
"""
from __future__ import annotations

from pathlib import Path

from app.services import audit_log_service


def test_audit_log_path_constant_present() -> None:
    p = getattr(audit_log_service, "_AUDIT_LOG_PATH", None)
    assert p is not None, "_AUDIT_LOG_PATH constant missing from audit_log_service."
    assert isinstance(p, Path), (
        f"_AUDIT_LOG_PATH must be a pathlib.Path; got {type(p).__name__}"
    )


def test_audit_log_path_filename_pin() -> None:
    p: Path = audit_log_service._AUDIT_LOG_PATH
    assert p.name == "audit.jsonl", (
        f"_AUDIT_LOG_PATH filename drift: expected 'audit.jsonl', got {p.name!r}. "
        "A silent rename would split the durable trail across two files."
    )


def test_audit_log_path_parent_pin() -> None:
    p: Path = audit_log_service._AUDIT_LOG_PATH
    assert p.parent.name == "logs", (
        f"_AUDIT_LOG_PATH parent drift: expected 'logs', got {p.parent.name!r}. "
        "A silent redirect of the trail directory would defeat downstream tail-watchers."
    )
