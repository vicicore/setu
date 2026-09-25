"""Proves the generic /journeys API is genuinely generic — the same
endpoints drive both life events, with the orchestrator/connector
resolution never hardcoding "college admission" or "scholarship"
anywhere. Starting a Small Business exercises three different mock
connectors (Labour, Urban Development, Finance) through the exact same
code path College Admission uses through Revenue."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _verify_via_vault(citizen_id: str, doc_type: str) -> None:
    upload = client.post(
        f"/api/v1/citizens/{citizen_id}/documents",
        data={"doc_type": doc_type},
        files={"file": (f"{doc_type}.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    document_id = upload.json()["id"]
    client.post(f"/api/v1/citizens/{citizen_id}/documents/{document_id}/submit-for-review")
    client.post(f"/api/v1/citizens/{citizen_id}/documents/{document_id}/verify")


def test_college_admission_via_generic_journeys_api() -> None:
    citizen_id = "citizen-generic-college-1"
    # This citizen has no seeded vault (unlike the /demo citizen) —
    # identity and domicile must be verified through the vault too,
    # proving the generic API doesn't secretly rely on demo-only seeding.
    _verify_via_vault(citizen_id, "identity_verification")
    _verify_via_vault(citizen_id, "domicile_certificate")

    started = client.post(
        f"/api/v1/citizens/{citizen_id}/journeys",
        json={"life_event_code": "college_admission_scholarship"},
    )
    assert started.status_code == 201
    body = started.json()
    application_id = body["application_id"]
    steps = {s["service_code"]: s for s in body["steps"]}
    assert steps["identity_verification"]["status"] == "verified"
    assert steps["domicile_certificate"]["status"] == "verified"
    scholarship = next(s for s in body["steps"] if s["service_code"] == "education_scholarship")
    assert scholarship["status"] == "blocked"
    assert body["current_blocker"] is not None
    assert "consent" in body["next_action"].lower()

    consent = client.post(
        f"/api/v1/journeys/{application_id}/consent/income_certificate",
        json={"purpose": "Verify income for scholarship"},
    )
    assert consent.status_code == 200

    submitted = client.post(f"/api/v1/journeys/{application_id}/submit/income_certificate", json={})
    assert submitted.status_code == 200
    steps = {s["service_code"]: s for s in submitted.json()["steps"]}
    assert steps["income_certificate"]["status"] == "in_progress"
    assert steps["income_certificate"]["external_reference"].startswith("REV-")

    approved = client.post(f"/api/v1/journeys/{application_id}/approve/income_certificate")
    assert approved.status_code == 200
    steps = {s["service_code"]: s for s in approved.json()["steps"]}
    assert steps["income_certificate"]["status"] == "verified"
    assert steps["education_scholarship"]["status"] == "ready"
    assert approved.json()["current_blocker"] is None

    listing = client.get(f"/api/v1/citizens/{citizen_id}/journeys").json()
    assert len(listing) == 1
    assert listing[0]["application_id"] == application_id


def test_start_small_business_end_to_end_through_three_connectors() -> None:
    citizen_id = "citizen-generic-business-1"
    started = client.post(
        f"/api/v1/citizens/{citizen_id}/journeys",
        json={"life_event_code": "start_small_business"},
    )
    assert started.status_code == 201
    application_id = started.json()["application_id"]
    steps = {s["service_code"]: s for s in started.json()["steps"]}
    assert steps["business_registration"]["status"] == "not_started"
    assert steps["local_noc"]["status"] == "blocked"
    assert steps["gst_registration"]["status"] == "blocked"

    def _run_service(service_code: str, expected_ref_prefix: str) -> None:
        client.post(
            f"/api/v1/journeys/{application_id}/consent/{service_code}",
            json={"purpose": f"Process {service_code}"},
        )
        submitted = client.post(f"/api/v1/journeys/{application_id}/submit/{service_code}", json={})
        assert submitted.status_code == 200
        step = next(s for s in submitted.json()["steps"] if s["service_code"] == service_code)
        assert step["status"] == "in_progress"
        assert step["external_reference"].startswith(expected_ref_prefix)
        approved = client.post(f"/api/v1/journeys/{application_id}/approve/{service_code}")
        assert approved.status_code == 200
        step = next(s for s in approved.json()["steps"] if s["service_code"] == service_code)
        assert step["status"] == "verified"

    _run_service("business_registration", "LAB-")

    after_registration = client.get(f"/api/v1/journeys/{application_id}").json()
    steps = {s["service_code"]: s for s in after_registration["steps"]}
    assert steps["local_noc"]["status"] == "ready"
    assert steps["gst_registration"]["status"] == "ready"
    # With every step now VERIFIED or READY, is_complete() is already
    # true (established semantics since Phase 2 — READY is a legitimate
    # terminal state, e.g. education_scholarship in the college flow).
    # The citizen can still choose to grant consent/submit local_noc and
    # gst_registration for their own record — proven by _run_service
    # succeeding below — even though the journey already reports complete.
    assert after_registration["is_complete"] is True

    _run_service("local_noc", "URB-")
    _run_service("gst_registration", "FIN-")

    final = client.get(f"/api/v1/journeys/{application_id}").json()
    assert final["is_complete"] is True
    assert final["current_blocker"] is None
    assert "nothing further" in final["next_action"].lower()


def test_identity_verification_has_a_registered_connector() -> None:
    """Regression test for a real bug found via live browser use: a
    citizen with no vault-pre-verified identity got "No connector
    registered for department 'Home'" the moment they tried to submit
    identity_verification — a path the /demo citizen's seeding always
    skipped, so no existing test caught it."""
    citizen_id = "citizen-identity-connector-test"
    started = client.post(
        f"/api/v1/citizens/{citizen_id}/journeys",
        json={"life_event_code": "college_admission_scholarship"},
    ).json()
    application_id = started["application_id"]

    client.post(
        f"/api/v1/journeys/{application_id}/consent/identity_verification",
        json={"purpose": "Verify identity"},
    )
    submitted = client.post(
        f"/api/v1/journeys/{application_id}/submit/identity_verification", json={}
    )
    assert submitted.status_code == 200
    step = next(
        s for s in submitted.json()["steps"] if s["service_code"] == "identity_verification"
    )
    assert step["status"] == "in_progress"
    assert step["external_reference"].startswith("HOM-")


def test_journey_not_found_returns_404() -> None:
    response = client.get("/api/v1/journeys/does-not-exist")
    assert response.status_code == 404


def test_document_rejection_cascades_and_leaves_requirement_unsatisfied() -> None:
    """Document -> Under Review -> Reject -> requirement stays
    unsatisfied -> the journey's next_action names an actionable step."""
    citizen_id = "citizen-rejection-test"
    started = client.post(
        f"/api/v1/citizens/{citizen_id}/journeys",
        json={"life_event_code": "college_admission_scholarship"},
    ).json()
    application_id = started["application_id"]

    upload = client.post(
        f"/api/v1/citizens/{citizen_id}/documents",
        data={"doc_type": "identity_verification"},
        files={"file": ("identity.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    document_id = upload.json()["id"]
    client.post(f"/api/v1/citizens/{citizen_id}/documents/{document_id}/submit-for-review")
    rejected = client.post(
        f"/api/v1/citizens/{citizen_id}/documents/{document_id}/reject",
        json={"reason": "Photo illegible"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Photo illegible"
    assert len(rejected.json()["used_by"]) == 1
    assert rejected.json()["used_by"][0]["application_id"] == application_id

    detail = client.get(f"/api/v1/journeys/{application_id}").json()
    identity_step = next(
        s for s in detail["steps"] if s["service_code"] == "identity_verification"
    )
    assert identity_step["status"] == "rejected"
    assert "rejected" in detail["next_action"].lower()


def test_consent_revoke_deactivates_consent() -> None:
    citizen_id = "citizen-revoke-test"
    started = client.post(
        f"/api/v1/citizens/{citizen_id}/journeys",
        json={"life_event_code": "start_small_business"},
    )
    application_id = started.json()["application_id"]
    client.post(
        f"/api/v1/journeys/{application_id}/consent/business_registration",
        json={"purpose": "test"},
    )
    revoked = client.post(
        f"/api/v1/journeys/{application_id}/consent/business_registration/revoke"
    )
    assert revoked.status_code == 200
    step = next(
        s for s in revoked.json()["steps"] if s["service_code"] == "business_registration"
    )
    assert step["consent"]["is_active"] is False

    blocked_submit = client.post(
        f"/api/v1/journeys/{application_id}/submit/business_registration", json={}
    )
    assert blocked_submit.status_code == 409
