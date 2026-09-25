"""Proves GET /api/v1/admin/metrics reflects real application state, not
placeholder numbers — the same journey mutated through /demo shows up
here with matching counts. Also proves it's admin-only."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import demo_scenario
from app.tests.conftest import login, login_admin

client = TestClient(app)


def test_metrics_requires_admin_role() -> None:
    client.post("/api/v1/demo/reset")
    _citizen_id, headers = login(client)

    unauthenticated = client.get("/api/v1/admin/metrics")
    assert unauthenticated.status_code == 401

    non_admin = client.get("/api/v1/admin/metrics", headers=headers)
    assert non_admin.status_code == 403


def test_metrics_reflect_a_blocked_journey() -> None:
    client.post("/api/v1/demo/reset")
    _admin_id, headers = login_admin(client)

    response = client.get("/api/v1/admin/metrics", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["total_journeys"] == 1
    assert body["active_journeys"] == 1
    assert body["blocked_journeys"] == 1
    assert body["bottleneck_service_codes"]["education_scholarship"] == 1
    detail = body["blocked_journey_details"][0]
    assert detail["citizen_id"] == demo_scenario.DEMO_CITIZEN_ID
    assert "education_scholarship" in detail["blocked_service_codes"]


def test_metrics_show_pending_department_after_submission() -> None:
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/demo/consent/income-certificate")
    client.post("/api/v1/demo/actions/submit-income-certificate")
    _admin_id, headers = login_admin(client)

    body = client.get("/api/v1/admin/metrics", headers=headers).json()
    assert body["department_pending_counts"]["Revenue"] == 1


def test_metrics_show_zero_blocked_once_scholarship_and_caste_resolve() -> None:
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/demo/consent/income-certificate")
    client.post("/api/v1/demo/actions/submit-income-certificate")
    client.post("/api/v1/demo/actions/approve-income-certificate")
    client.post("/api/v1/demo/actions/submit-caste-certificate-for-review")
    client.post("/api/v1/demo/actions/verify-caste-certificate")
    _admin_id, headers = login_admin(client)

    body = client.get("/api/v1/admin/metrics", headers=headers).json()
    assert body["blocked_journeys"] == 0
    assert body["complete_journeys"] == 1
