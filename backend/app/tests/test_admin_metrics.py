"""Proves GET /api/v1/admin/metrics reflects real application state, not
placeholder numbers — the same journey mutated through /demo shows up
here with matching counts."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_metrics_reflect_a_blocked_journey() -> None:
    client.post("/api/v1/demo/reset")

    response = client.get("/api/v1/admin/metrics")
    assert response.status_code == 200
    body = response.json()

    assert body["total_journeys"] == 1
    assert body["active_journeys"] == 1
    assert body["blocked_journeys"] == 1
    assert body["bottleneck_service_codes"]["education_scholarship"] == 1
    detail = body["blocked_journey_details"][0]
    assert detail["citizen_id"] == "demo-citizen-priya-deshmukh"
    assert "education_scholarship" in detail["blocked_service_codes"]


def test_metrics_show_pending_department_after_submission() -> None:
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/demo/consent/income-certificate")
    client.post("/api/v1/demo/actions/submit-income-certificate")

    body = client.get("/api/v1/admin/metrics").json()
    assert body["department_pending_counts"]["Revenue"] == 1


def test_metrics_show_zero_blocked_once_scholarship_and_caste_resolve() -> None:
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/demo/consent/income-certificate")
    client.post("/api/v1/demo/actions/submit-income-certificate")
    client.post("/api/v1/demo/actions/approve-income-certificate")
    client.post("/api/v1/demo/actions/submit-caste-certificate-for-review")
    client.post("/api/v1/demo/actions/verify-caste-certificate")

    body = client.get("/api/v1/admin/metrics").json()
    assert body["blocked_journeys"] == 0
    assert body["complete_journeys"] == 1
