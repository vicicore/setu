"""Drives the /demo HTTP surface end to end, proving the mandatory
`/demo` experience (Master Prompt section 9) produces real backend state
changes — through the repository-backed service layer, not an in-memory
singleton — via actual API calls."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_demo_catalog_describes_the_signature_journey() -> None:
    response = client.get("/api/v1/demo/catalog")
    assert response.status_code == 200
    body = response.json()
    codes = {s["service_code"] for s in body["services"]}
    assert codes == {
        "identity_verification",
        "domicile_certificate",
        "caste_certificate",
        "income_certificate",
        "education_scholarship",
    }
    scholarship = next(s for s in body["services"] if s["service_code"] == "education_scholarship")
    assert scholarship["depends_on_service_code"] == "income_certificate"


def test_demo_reset_returns_seeded_blocked_scholarship() -> None:
    response = client.post("/api/v1/demo/reset")
    assert response.status_code == 200
    body = response.json()

    steps_by_code = {s["service_code"]: s for s in body["steps"]}
    assert steps_by_code["identity_verification"]["status"] == "verified"
    assert steps_by_code["income_certificate"]["status"] == "not_started"
    assert steps_by_code["education_scholarship"]["status"] == "blocked"
    assert body["is_complete"] is False


def test_demo_full_flow_unlocks_scholarship_via_http_and_persists() -> None:
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
    assert steps["income_certificate"]["sla_due_at"] is not None
    assert steps["education_scholarship"]["status"] == "blocked"

    # State must be readable back via GET, independent of the POST that
    # produced it — proves it went through the repository, not just a
    # response echoed from request-local memory.
    reread = client.get("/api/v1/demo/journey")
    assert reread.json()["steps"] == submitted.json()["steps"]

    approved = client.post("/api/v1/demo/actions/approve-income-certificate")
    assert approved.status_code == 200
    steps = {s["service_code"]: s for s in approved.json()["steps"]}
    assert steps["income_certificate"]["status"] == "verified"
    assert steps["education_scholarship"]["status"] == "ready"
    assert approved.json()["is_complete"] is True

    # Every transition must have left an audit trail entry.
    audit_log = client.get("/api/v1/demo/audit-log").json()
    actions = [entry["action"] for entry in audit_log]
    assert actions == [
        "journey.reset",
        "consent.granted",
        "connector.submitted",
        "connector.event_received",
    ]
    cascade_entry = next(e for e in audit_log if e["action"] == "connector.event_received")
    assert "education_scholarship" in cascade_entry["metadata"]["cascaded_to"]
