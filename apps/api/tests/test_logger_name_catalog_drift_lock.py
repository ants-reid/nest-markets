"""Drift-lock pin: module-level ``_logger = logging.getLogger(__name__)``
binding must remain in safety-relevant modules.

Cycle 63 — MH-DRIFTLOCK-LOGGER-NAME-CATALOG.

Why this pin exists
-------------------
Cycle 61's lifespan log-floor test pins specific log substrings; cycle
62 SHA-256-pinned the lifespan body.  Both rely on the modules
continuing to bind their loggers under a stable name (``_logger``).
A silent rename to ``log`` / ``LOG`` / ``logger`` would break the
log-line guards' grep targets without flipping any of the existing
pins.  This test pins the binding line itself.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import re
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent / "app"

# Modules that MUST expose a module-level _logger bound to
# logging.getLogger(__name__). Each entry is the path relative to
# apps/api/app/.
EXPECTED_LOGGER_MODULES: tuple[str, ...] = (
    "main.py",
    "services/broker_service.py",
    "services/broker_mode_guard.py",
    "workers/auto_paper_trader_worker.py",
    "workers/auto_paper_close_worker.py",
)

_LOGGER_RE = re.compile(
    r"^_logger\s*=\s*logging\.getLogger\(__name__\)\s*$",
    re.MULTILINE,
)


def test_safety_modules_define_module_level_logger() -> None:
    drift: list[str] = []
    for rel in EXPECTED_LOGGER_MODULES:
        path = APP_ROOT / rel
        if not path.exists():
            drift.append(f"  MISSING module: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if not _LOGGER_RE.search(text):
            drift.append(
                f"  {rel}: no module-level "
                "`_logger = logging.getLogger(__name__)` binding found"
            )
    assert not drift, (
        "Safety-module logger binding drift detected. The lifespan "
        "log-floor pin and worker-execute pin both assume these modules "
        "expose a module-level `_logger`. A rename or removal would "
        "silently bypass those guards.\n" + "\n".join(drift)
    )


def test_logger_binding_count_floor() -> None:
    """Floor: at least 5 safety-relevant modules must continue to bind
    the canonical logger name. Catches silent reductions."""
    matches = 0
    for rel in EXPECTED_LOGGER_MODULES:
        path = APP_ROOT / rel
        if path.exists() and _LOGGER_RE.search(path.read_text(encoding="utf-8")):
            matches += 1
    assert matches >= 5, (
        f"Only {matches} safety modules expose `_logger = "
        "logging.getLogger(__name__)`; floor is 5. Either restore the "
        "binding(s) or update the catalog with explicit ledger entry."
    )


def test_no_alternative_top_level_logger_name_in_safety_modules() -> None:
    """Forbid silently shadowing the canonical name with a differently
    named module-level logger (`log`, `LOG`, `logger`)."""
    forbidden_re = re.compile(
        r"^(?:log|LOG|logger)\s*=\s*logging\.getLogger\(__name__\)\s*$",
        re.MULTILINE,
    )
    offenders: list[str] = []
    for rel in EXPECTED_LOGGER_MODULES:
        path = APP_ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in forbidden_re.finditer(text):
            offenders.append(f"  {rel}: forbidden binding `{m.group(0).strip()}`")
    assert not offenders, (
        "A safety module introduced a non-canonical module-level logger "
        "name. Use `_logger = logging.getLogger(__name__)`.\n"
        + "\n".join(offenders)
    )
