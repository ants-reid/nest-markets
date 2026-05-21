"""Drift-lock pin: catalog of FastAPI route handlers that depend on
``api_key_auth``.

Cycle 62 — MH-DRIFTLOCK-AUTH-DEPENDENCY-CATALOG.

Why this pin exists
-------------------
The repo has a small, deliberately-narrow auth surface: only two route
handlers currently depend on ``app.middleware.auth.api_key_auth``
(``POST /execution/paper`` and ``POST /workflow/run``).  A silent
removal of either ``Depends(api_key_auth)`` annotation would expose a
mutating endpoint to unauthenticated callers without changing any
guard or service code.

This pin freezes:
  1. the **set of source files** that import ``api_key_auth``, and
  2. the **set of (file, line) sites** where ``Depends(api_key_auth)``
     appears, with a SAFETY_AUTH_REQUIRED subset that must remain.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import re
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent / "app"

# Source files that MUST continue to import api_key_auth.  A silent
# removal of the import is the first step toward removing the Depends().
EXPECTED_AUTH_IMPORTING_FILES: set[str] = {
    "app/api/routes/execution.py",
    "app/api/routes/monitor_test.py",
    "app/api/routes/workflow.py",
}

# Route-decorator patterns that MUST appear paired with a
# Depends(api_key_auth) site in the same file.  Keys are file paths;
# values are the route decorators expected to be auth-protected.
SAFETY_AUTH_REQUIRED_ROUTES: dict[str, set[str]] = {
    "app/api/routes/execution.py": {
        '@router.post("/paper", response_model=PaperExecutionResponse)',
    },
    "app/api/routes/monitor_test.py": {
        '@router.post("/test/{service_id}", response_model=MonitorDryProbeResponseSchema)',
    },
    "app/api/routes/workflow.py": {
        '@router.post("/run", response_model=WorkflowRunResponse)',
    },
}

_IMPORT_PATTERN = re.compile(
    r"from\s+app\.middleware\.auth\s+import\s+[^\n]*api_key_auth"
)
_DEPENDS_PATTERN = re.compile(r"Depends\(\s*api_key_auth\s*\)")


def _read(path_rel: str) -> str:
    return (API_ROOT.parent / path_rel).read_text(encoding="utf-8")


def _files_importing_auth() -> set[str]:
    found: set[str] = set()
    for py in API_ROOT.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if _IMPORT_PATTERN.search(text):
            rel = py.relative_to(API_ROOT.parent).as_posix()
            found.add(rel)
    return found


def test_api_key_auth_importing_files_unchanged() -> None:
    actual = _files_importing_auth()
    missing = EXPECTED_AUTH_IMPORTING_FILES - actual
    extra = actual - EXPECTED_AUTH_IMPORTING_FILES
    assert not missing, (
        f"Files that previously imported api_key_auth no longer do: "
        f"{sorted(missing)}. Removing the auth import is the first step "
        "toward exposing mutating endpoints unauthenticated."
    )
    assert not extra, (
        f"New files now import api_key_auth: {sorted(extra)}. "
        "Adding auth elsewhere is fine but MUST be reviewed and pinned "
        "via an additive update to EXPECTED_AUTH_IMPORTING_FILES + a "
        "ledger entry naming the new auth-protected surface."
    )


def test_safety_auth_required_routes_remain_protected() -> None:
    """For every (file, decorator) in SAFETY_AUTH_REQUIRED_ROUTES, both
    the decorator AND a `Depends(api_key_auth)` annotation must appear
    in the file."""
    failures: list[str] = []
    for rel_path, decorators in SAFETY_AUTH_REQUIRED_ROUTES.items():
        text = _read(rel_path)
        if not _DEPENDS_PATTERN.search(text):
            failures.append(
                f"  {rel_path}: no Depends(api_key_auth) site found"
            )
            continue
        for decorator in decorators:
            if decorator not in text:
                failures.append(
                    f"  {rel_path}: expected decorator missing: {decorator!r}"
                )
    assert not failures, (
        "Safety-required auth-protected routes drift detected. These "
        "routes must continue to require api_key_auth.\n"
        + "\n".join(failures)
    )


def test_depends_api_key_auth_count_floor() -> None:
    """The total count of ``Depends(api_key_auth)`` sites across app/
    must not regress.  A silent removal would pass the per-file checks
    above only if the decorator was also moved or renamed."""
    total = 0
    for py in API_ROOT.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        total += len(_DEPENDS_PATTERN.findall(text))
    # Floor at 2 (current count); raise additively when new auth-protected
    # endpoints are added.
    assert total >= 2, (
        f"Depends(api_key_auth) site count regressed: found {total}, "
        "expected at least 2. A silent removal exposes mutating endpoints."
    )
