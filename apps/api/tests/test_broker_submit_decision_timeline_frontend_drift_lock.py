"""Drift-lock: broker submit decision timeline frontend stays read-only.

The cockpit timeline at ``/cockpit/audit/broker-submit-decisions`` and
its client helper at ``lib/api/brokerSubmitDecisions.ts`` must remain
strictly read-only. They must not import the broker submit helper,
must not reference the executable broker submit seam, and must not
reference the simulator route.

This is the frontend twin of the route-surface pin: if either side
silently grew a submission/cancellation/retry call, this test catches
it before it can ship.

Drift-lock notes:
    * Test-only / additive; no production code change.
    * Auto trading, live trading, and worker submit authority are
      unaffected.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TIMELINE_PAGE = (
    _REPO_ROOT
    / "apps"
    / "web"
    / "app"
    / "cockpit"
    / "audit"
    / "broker-submit-decisions"
    / "page.tsx"
)
_CLIENT_HELPER = (
    _REPO_ROOT
    / "apps"
    / "web"
    / "lib"
    / "api"
    / "brokerSubmitDecisions.ts"
)
_CLIENT_HELPER_EXPECTED_ROUTE = "/broker/submit-decisions/recent"

_COCKPIT_AUDIT_INDEX = (
    _REPO_ROOT
    / "apps"
    / "web"
    / "app"
    / "cockpit"
    / "audit"
    / "page.tsx"
)
_EXPECTED_TIMELINE_HREF = "/cockpit/audit/broker-submit-decisions"

# Forbidden identifiers/strings — appearance of any of these on the
# timeline page or its client helper would mean the read-only audit
# surface has acquired a submit/mutation path.
FORBIDDEN_IDENTIFIERS: tuple[str, ...] = (
    "submitBrokerOrder",
    "cancelBrokerOrder",
    "submitOrder",
)
FORBIDDEN_ROUTE_LITERALS: tuple[str, ...] = (
    '"/broker/orders"',
    "'/broker/orders'",
    '"/execution/paper"',
    "'/execution/paper'",
)
FORBIDDEN_IMPORT_FRAGMENTS: tuple[str, ...] = (
    '/lib/api/broker"',
    "/lib/api/broker'",
)


def _read(path: Path) -> str:
    assert path.exists(), f"Expected timeline asset missing: {path}"
    return path.read_text(encoding="utf-8")


def test_timeline_page_exists() -> None:
    assert _TIMELINE_PAGE.exists(), (
        f"Timeline page missing at {_TIMELINE_PAGE}. The cockpit audit "
        "route /cockpit/audit/broker-submit-decisions has been removed "
        "or moved without updating this drift-lock pin."
    )


def test_timeline_page_does_not_import_submit_helpers() -> None:
    source = _read(_TIMELINE_PAGE)
    leaks = [name for name in FORBIDDEN_IDENTIFIERS if name in source]
    assert not leaks, (
        f"Timeline page imported/referenced submit helper(s) {leaks}. "
        "The audit timeline must remain strictly read-only."
    )


def test_timeline_page_does_not_reference_submit_or_simulator_routes() -> None:
    source = _read(_TIMELINE_PAGE)
    leaks = [
        literal for literal in FORBIDDEN_ROUTE_LITERALS if literal in source
    ]
    assert not leaks, (
        f"Timeline page referenced executable/simulator route literal(s) "
        f"{leaks}. The audit timeline must not call /broker/orders or "
        "/execution/paper."
    )


def test_timeline_page_does_not_import_from_broker_lib() -> None:
    source = _read(_TIMELINE_PAGE)
    leaks = [
        frag for frag in FORBIDDEN_IMPORT_FRAGMENTS if frag in source
    ]
    assert not leaks, (
        f"Timeline page imported from the broker submit lib (fragments "
        f"{leaks}). That lib hosts submitBrokerOrder; the audit page "
        "must not depend on it."
    )


def test_client_helper_calls_only_the_read_only_audit_route() -> None:
    source = _read(_CLIENT_HELPER)
    assert _CLIENT_HELPER_EXPECTED_ROUTE in source, (
        f"Client helper no longer references the audit route "
        f"{_CLIENT_HELPER_EXPECTED_ROUTE!r}."
    )
    leaks = [
        literal for literal in FORBIDDEN_ROUTE_LITERALS if literal in source
    ]
    assert not leaks, (
        f"Client helper referenced executable/simulator route literal(s) "
        f"{leaks}. The timeline client must call only the read-only audit "
        "feed."
    )
    forbidden_methods = ('method: "POST"', 'method: "PUT"',
                         'method: "PATCH"', 'method: "DELETE"')
    method_leaks = [m for m in forbidden_methods if m in source]
    assert not method_leaks, (
        f"Client helper issued a non-GET request {method_leaks}. The "
        "timeline client must remain GET-only."
    )


def test_client_helper_does_not_export_submit_function() -> None:
    source = _read(_CLIENT_HELPER)
    leaks = [name for name in FORBIDDEN_IDENTIFIERS if name in source]
    assert not leaks, (
        f"Client helper defined/exported submit identifier(s) {leaks}. "
        "The timeline client must expose only read-only helpers."
    )


def test_timeline_page_advertises_read_only_posture() -> None:
    """The page UI must keep advertising its read-only posture; this
    is the user-visible safety signal that the cockpit relies on."""
    source = _read(_TIMELINE_PAGE).lower()
    assert "read-only" in source, (
        "Timeline page no longer advertises 'read-only' in its UI text; "
        "the operator-facing safety signal has been removed."
    )


# ── cockpit audit landing link pin ──────────────────────────────────────


def test_cockpit_audit_index_links_to_timeline_page() -> None:
    """The cockpit audit hub at /cockpit/audit must keep linking to the
    read-only broker submit decision timeline. If this fails, the
    timeline page has been silently delisted from the audit hub or the
    href shape has drifted; both are user-visible regressions."""
    source = _read(_COCKPIT_AUDIT_INDEX)
    assert _EXPECTED_TIMELINE_HREF in source, (
        f"Cockpit audit hub no longer references the timeline href "
        f"{_EXPECTED_TIMELINE_HREF!r}. The audit landing page must "
        "expose the broker submit decision timeline tile."
    )


def test_cockpit_audit_index_tile_advertises_broker_submit_decisions() -> None:
    """The audit-hub tile copy must keep naming the broker submit
    decision feed so operators can find it. Drift here would be silent
    UI rot rather than a safety bug."""
    source = _read(_COCKPIT_AUDIT_INDEX).lower()
    assert "broker submit decision" in source, (
        "Cockpit audit hub no longer mentions 'broker submit decision' "
        "in its tile copy; the timeline tile description has drifted."
    )


def test_cockpit_audit_index_uses_audit_client_helper() -> None:
    """The audit-hub tile must keep loading its row count via the
    read-only ``getRecentBrokerSubmitDecisions`` helper. If this fails,
    the tile may have been wired to a non-audit helper."""
    source = _read(_COCKPIT_AUDIT_INDEX)
    assert "getRecentBrokerSubmitDecisions" in source, (
        "Cockpit audit hub no longer imports getRecentBrokerSubmitDecisions; "
        "the audit-hub tile is not reading from the read-only audit feed."
    )


# ── timeline page body SHA pin ──────────────────────────────────────────
#
# Pin the full source of the timeline page. Visual/layout/control changes
# to the audit timeline page now require a deliberate hash update, which
# forces a review that the page remains read-only, submit-free,
# /broker/orders-free, and /execution/paper-free.

_EXPECTED_TIMELINE_PAGE_SHA = (
    "18af398acafee3b81c41a97a95b3bbcfdec3c2382fdd0b27a9dd6daf4174ba87"
)
_EXPECTED_TIMELINE_PAGE_LEN = 16723


def test_submit_decisions_timeline_page_body_hash_is_pinned() -> None:
    """SHA-pin the timeline page body.

    If this fails because of an intentional edit, recompute::

        cd <repo root>
        python -c 'import hashlib, pathlib; \
            p=pathlib.Path("apps/web/app/cockpit/audit/broker-submit-decisions/page.tsx"); \
            t=p.read_text(encoding="utf-8"); \
            print(hashlib.sha256(t.encode()).hexdigest(), len(t))'

    Then update ``_EXPECTED_TIMELINE_PAGE_SHA`` /
    ``_EXPECTED_TIMELINE_PAGE_LEN`` AFTER confirming the page remains
    read-only, submit-free, and does NOT introduce any reference to
    ``/broker/orders``, ``/execution/paper``, ``submitBrokerOrder``,
    ``cancelBrokerOrder``, or ``submitOrder``.
    """
    text = _read(_TIMELINE_PAGE)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    length = len(text)
    assert sha == _EXPECTED_TIMELINE_PAGE_SHA and length == _EXPECTED_TIMELINE_PAGE_LEN, (
        "Timeline page body drift: expected "
        f"sha256={_EXPECTED_TIMELINE_PAGE_SHA} len={_EXPECTED_TIMELINE_PAGE_LEN}; "
        f"got sha256={sha} len={length}. "
        "Re-verify the page is still read-only and submit-free before "
        "updating the pin."
    )


# ── audit-hub count contract pin ────────────────────────────────────────
#
# The broker-submit-decisions tile on the cockpit audit hub derives its
# row-count display from the *envelope* ``count`` field returned by the
# audit feed. Pin that contract so a schema-keyed refactor cannot
# silently zero the tile by switching to ``items.length`` or a wrong
# field name.

_AUDIT_HUB_FORBIDDEN_COUNT_DERIVATIONS: tuple[str, ...] = (
    "resp.items.length",
    "resp.items?.length",
    "resp?.items?.length",
    "response.items.length",
    "resp.total",
    "resp.size",
    "resp.length",
)


def _extract_broker_submit_decisions_tile_block(source: str) -> str:
    """Return the substring of ``apps/web/app/cockpit/audit/page.tsx``
    that starts at the broker-submit-decisions tile's ``href`` literal
    and ends at the closing brace of that tile's ``loadCount``
    arrow-function body (matched with balanced-brace scanning).

    This bounds the count-contract assertion to the broker-submit
    tile only, avoiding false positives from neighbouring tiles."""
    href = _EXPECTED_TIMELINE_HREF
    start = source.find(href)
    assert start != -1, (
        f"Audit hub no longer contains the timeline href {href!r}; "
        "the broker-submit-decisions tile is gone."
    )
    # Find loadCount: async () => { ... after this position.
    m = re.search(r"loadCount:\s*async\s*\(\s*\)\s*=>\s*\{", source[start:])
    assert m is not None, (
        "Could not find loadCount arrow-function for the broker-submit "
        "tile; the audit-hub tile shape has drifted."
    )
    brace_open = start + m.end() - 1
    depth = 1
    j = brace_open + 1
    while depth > 0 and j < len(source):
        c = source[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        j += 1
    assert depth == 0, (
        "Unbalanced braces in audit-hub loadCount; the audit-hub tile "
        "shape has drifted."
    )
    return source[start:j]


def test_audit_hub_broker_submit_decisions_count_uses_envelope_count() -> None:
    """The broker-submit-decisions tile must derive its count from the
    audit envelope's ``count`` field, not from ``items.length`` or a
    fabricated field. A silent switch would zero the tile."""
    source = _read(_COCKPIT_AUDIT_INDEX)
    block = _extract_broker_submit_decisions_tile_block(source)
    assert "getRecentBrokerSubmitDecisions" in block, (
        "Broker-submit-decisions tile no longer calls "
        "getRecentBrokerSubmitDecisions inside its loadCount; the tile "
        "is not reading from the read-only audit feed."
    )
    assert "resp.count" in block, (
        "Broker-submit-decisions tile loadCount no longer returns "
        "'resp.count'. The cockpit audit hub must derive the row count "
        "from the audit envelope's `count` field, not from "
        "`items.length` or any other derived value (which would "
        "silently zero the tile if items are paginated or filtered)."
    )
    leaks = [
        pattern for pattern in _AUDIT_HUB_FORBIDDEN_COUNT_DERIVATIONS
        if pattern in block
    ]
    assert not leaks, (
        f"Broker-submit-decisions tile loadCount uses forbidden count "
        f"derivation(s) {leaks}. Use the envelope `count` field instead."
    )
