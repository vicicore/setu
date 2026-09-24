"""Drives the /demo HTTP surface end to end, proving the mandatory
`/demo` experience (Master Prompt section 9) produces real backend state
changes through actual API calls, not client-side fakery."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import demo_store

client = TestClient(app)


def setup_function() -> None:
    demo_store._demo_session = None


def test_demo_reset_returns_seeded_blocked_scholarship() -> None:
    response = client.post("/api/v1/demo/reset")
    assert response.status_code == 200
    body = response.json()

    steps_by_code = {s["service_code"]: s for s in body["steps"]}
    assert steps_by_code["identity_verification"]["status"] == "verified"
    assert steps_by_code["income_certificate"]["status"] == "not_started"
    assert steps_by_code["education_scholarship"]["status"] == "blocked"
    assert body["is_complete"] is False


def test_demo_full_flow_unlocks_scholarship_via_http() -> None:
    client.post("/api/v1/demo/reset")

    # Submitting without consent must fail over HTTP too (409), not just
    # in the domain layer.
    failed = client.post("/api/v1/demo/actions/submit-income-certificate")
    assert failed.status_code == 409

    client.post("/api/v1/demo/consent/income-certificate")
    submitted = client.post("/api/v1/demo/actions/submit-income-certificate")
    assert submitted.status_code == 200
    steps = {s["service_code"]: s for s in submitted.json()["steps"]}
    assert steps["income_certificate"]["status"] == "in_progress"
    assert steps["income_certificate"]["external_reference"].startswith("REV-")
    assert steps["education_scholarship"]["status"] == "blocked"

    approved = client.post("/api/v1/demo/actions/approve-income-certificate")
    assert approved.status_code == 200
    steps = {s["service_code"]: s for s in approved.json()["steps"]}
    assert steps["income_certificate"]["status"] == "verified"
    assert steps["education_scholarship"]["status"] == "ready"
    assert approved.json()["is_complete"] is True
