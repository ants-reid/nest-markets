"""Route-level tests for GET /prompts and GET /prompts/{subdir}/{filename}.

QA-081: Prompts route returns prompt list and content.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_prompts_returns_200_and_known_files() -> None:
    """QA-081a: GET /prompts lists at least the canonical system prompts."""
    response = client.get("/prompts")
    assert response.status_code == 200
    body = response.json()
    assert "prompts" in body
    assert isinstance(body["prompts"], list)
    assert "system/signal_engine_v1.md" in body["prompts"]
    assert "system/catalyst_classifier_v1.md" in body["prompts"]
    assert "user/signal_input_template_v1.md" in body["prompts"]


def test_get_prompt_returns_content() -> None:
    """QA-081b: GET /prompts/system/{filename} returns name and non-empty content."""
    response = client.get("/prompts/system/signal_engine_v1.md")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "system/signal_engine_v1.md"
    assert isinstance(body["content"], str)
    assert len(body["content"]) > 0


def test_get_prompt_unknown_file_returns_404() -> None:
    """QA-081c: GET /prompts/system/nonexistent.md returns 404."""
    response = client.get("/prompts/system/nonexistent_prompt.md")
    assert response.status_code == 404


def test_get_prompt_disallowed_subdir_returns_404() -> None:
    """QA-081d: GET /prompts/schemas/... returns 404 (schemas not exposed)."""
    response = client.get("/prompts/etc/passwd")
    assert response.status_code == 404
