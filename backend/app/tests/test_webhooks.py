"""Proves POST /api/v1/webhooks/n8n/{event} drives the exact same
orchestration state machine as the /demo approve action — no second,
webhook-specific implementation of dependency resolution or cascading
unlock (Phase 4 priority 1)."""

from fastapi.testclient import TestClient

from app.core import container
from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def _start_and_submit_income_certificate() -> str:
    """Drives the /demo flow up to "submitted" and returns the
    external_reference a webhook would report against."""
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/demo/consent/income-certificate")
    submitted = client.post("/api/v1/demo/actions/submit-income-certificate")
    steps = {s["service_code"]: s for s in submitted.json()["steps"]}
    return steps["income_certificate"]["external_reference"]


def test_webhook_approval_unlocks_scholarship_same_as_demo_action() -> None:
    external_reference = _start_and_submit_income_certificate()

    response = client.post(
        "/api/v1/webhooks/n8n/revenue.application.status_changed",
        json={
            "external_reference": external_reference,
            "service_code": "income_certificate",
            "status": "approved",
            "department": "Revenue",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted_status"] == "approved"
    assert body["application_id"] is not None

    journey = client.get("/api/v1/demo/journey").json()
    steps = {s["service_code"]: s for s in journey["steps"]}
    assert steps["income_certificate"]["status"] == "verified"
    assert steps["education_scholarship"]["status"] == "ready"

    audit_log = client.get("/api/v1/demo/audit-log").json()
    cascade_entry = next(e for e in audit_log if e["action"] == "connector.event_received")
    assert cascade_entry["metadata"]["source"] == "n8n_webhook:revenue.application.status_changed"
    assert "education_scholarship" in cascade_entry["metadata"]["cascaded_to"]


def test_webhook_rejects_unknown_external_reference() -> None:
    response = client.post(
        "/api/v1/webhooks/n8n/revenue.application.status_changed",
        json={
            "external_reference": "REV-does-not-exist",
            "service_code": "income_certificate",
            "status": "approved",
            "department": "Revenue",
        },
    )
    assert response.status_code == 404


def test_webhook_ignores_non_terminal_status_without_mutating_state() -> None:
    external_reference = _start_and_submit_income_certificate()

    response = client.post(
        "/api/v1/webhooks/n8n/revenue.application.status_changed",
        json={
            "external_reference": external_reference,
            "service_code": "income_certificate",
            "status": "submitted",
            "department": "Revenue",
        },
    )
    assert response.status_code == 200
    assert response.json()["accepted_status"] == "ignored"

    journey = client.get("/api/v1/demo/journey").json()
    steps = {s["service_code"]: s for s in journey["steps"]}
    assert steps["income_certificate"]["status"] == "in_progress"


def test_webhook_requires_matching_secret_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("N8N_WEBHOOK_SECRET", "top-secret")
    get_settings.cache_clear()
    container.get_journey_service.cache_clear()
    try:
        external_reference = _start_and_submit_income_certificate()

        unauthenticated = client.post(
            "/api/v1/webhooks/n8n/revenue.application.status_changed",
            json={
                "external_reference": external_reference,
                "service_code": "income_certificate",
                "status": "approved",
                "department": "Revenue",
            },
        )
        assert unauthenticated.status_code == 401

        authenticated = client.post(
            "/api/v1/webhooks/n8n/revenue.application.status_changed",
            json={
                "external_reference": external_reference,
                "service_code": "income_certificate",
                "status": "approved",
                "department": "Revenue",
            },
            headers={"x-setu-webhook-secret": "top-secret"},
        )
        assert authenticated.status_code == 200
    finally:
        get_settings.cache_clear()
        container.get_journey_service.cache_clear()
