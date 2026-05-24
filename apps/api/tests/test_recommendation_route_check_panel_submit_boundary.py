"""Frontend drift lock for the in-flight recommendation review panel.

The cockpit recommendation route-check panel must stay on the read-only
recommendation-owned helpers and must not import the actual broker submit
helper. This keeps the review chain off the executable ``/broker/orders``
submit seam until a separate guarded future phase explicitly authorizes it.
"""

from __future__ import annotations

from pathlib import Path


def test_recommendation_route_check_panel_does_not_import_submit_broker_order():
    repo_root = Path(__file__).resolve().parents[3]
    panel_path = repo_root / "apps" / "web" / "components" / "RecommendationRouteCheckPanel.tsx"

    source = panel_path.read_text(encoding="utf-8")

    assert 'from "../lib/api/paperRecommendations"' in source
    assert 'from "../lib/manualPaperSubmitReview"' in source
    assert "submitBrokerOrder" not in source
    assert 'from "../lib/api/broker"' not in source


def test_manual_paper_submit_confirmation_page_is_the_only_cockpit_surface_allowed_to_import_submit_broker_order():
    repo_root = Path(__file__).resolve().parents[3]
    page_path = (
        repo_root
        / "apps"
        / "web"
        / "app"
        / "cockpit"
        / "manual-paper-submit-confirmation"
        / "page.tsx"
    )

    source = page_path.read_text(encoding="utf-8")

    assert 'from "../../../lib/api/paperRecommendations"' in source
    assert 'from "../../../lib/api/broker"' in source
    assert "submitBrokerOrder" in source


def test_manual_paper_submit_review_helper_does_not_import_submit_broker_order():
    repo_root = Path(__file__).resolve().parents[3]
    helper_path = repo_root / "apps" / "web" / "lib" / "manualPaperSubmitReview.ts"

    source = helper_path.read_text(encoding="utf-8")

    assert 'from "./api/paperRecommendations"' in source
    assert "submitBrokerOrder" not in source
    assert 'from "./api/broker"' not in source