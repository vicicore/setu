"""Proves the eligibility engine is a deterministic rule evaluator over
the dependency graph — not an LLM guess — and gives a plain-language
reason for every status, matching Master Prompt section 16 (AI may
explain, but must never be the sole authority on eligibility)."""

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import ApplicationStepStatus
from app.services import eligibility
from app.services.dependency_graph import COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH

client = TestClient(app)


def test_evaluate_reflects_missing_income_certificate_blocking_scholarship() -> None:
    result = eligibility.evaluate(
        life_event_code="college_admission_scholarship",
        graph=COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
        verified_service_codes={"identity_verification", "domicile_certificate", "caste_certificate"},
    )
    by_code = {s.service_code: s for s in result.services}

    assert by_code["identity_verification"].status == ApplicationStepStatus.VERIFIED
    assert by_code["income_certificate"].status == ApplicationStepStatus.NOT_STARTED
    scholarship = by_code["education_scholarship"]
    assert scholarship.status == ApplicationStepStatus.BLOCKED
    assert "Income Certificate" in scholarship.reasons[0]
    assert result.overall_ready is False


def test_evaluate_marks_scholarship_ready_once_income_is_verified() -> None:
    result = eligibility.evaluate(
        life_event_code="college_admission_scholarship",
        graph=COLLEGE_ADMISSION_SCHOLARSHIP_GRAPH,
        verified_service_codes={
            "identity_verification", "domicile_certificate", "caste_certificate", "income_certificate",
        },
    )
    by_code = {s.service_code: s for s in result.services}
    assert by_code["education_scholarship"].status == ApplicationStepStatus.READY
    assert result.overall_ready is True


def test_eligibility_raw_endpoint_returns_reasons_over_http() -> None:
    response = client.post(
        "/api/v1/eligibility/evaluate-raw",
        json={
            "life_event_code": "college_admission_scholarship",
            "verified_service_codes": ["identity_verification", "domicile_certificate", "caste_certificate"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    scholarship = next(s for s in body["services"] if s["service_code"] == "education_scholarship")
    assert scholarship["status"] == "blocked"
    assert set(scholarship["requires_service_codes"]) == {
        "identity_verification", "domicile_certificate", "income_certificate",
    }
    assert body["overall_ready"] is False


def test_eligibility_raw_endpoint_rejects_unknown_life_event() -> None:
    response = client.post(
        "/api/v1/eligibility/evaluate-raw",
        json={"life_event_code": "not_a_real_life_event", "verified_service_codes": []},
    )
    assert response.status_code == 404


def test_citizen_eligibility_endpoint_derives_verified_set_from_vault() -> None:
    """The normal flow: no verified_service_codes in the request at
    all — the endpoint computes it from the citizen's actual vault."""
    citizen_id = "citizen-eligibility-vault-test"

    before = client.get(
        f"/api/v1/citizens/{citizen_id}/eligibility/college_admission_scholarship"
    )
    assert before.status_code == 200
    scholarship = next(
        s for s in before.json()["services"] if s["service_code"] == "education_scholarship"
    )
    assert scholarship["status"] == "blocked"

    for doc_type in ("identity_verification", "domicile_certificate", "income_certificate"):
        upload = client.post(
            f"/api/v1/citizens/{citizen_id}/documents",
            data={"doc_type": doc_type},
            files={"file": (f"{doc_type}.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        document_id = upload.json()["id"]
        client.post(f"/api/v1/citizens/{citizen_id}/documents/{document_id}/submit-for-review")
        client.post(f"/api/v1/citizens/{citizen_id}/documents/{document_id}/verify")

    after = client.get(
        f"/api/v1/citizens/{citizen_id}/eligibility/college_admission_scholarship"
    )
    scholarship = next(
        s for s in after.json()["services"] if s["service_code"] == "education_scholarship"
    )
    assert scholarship["status"] == "ready"
    assert after.json()["overall_ready"] is True


def test_citizen_eligibility_reflects_connector_verified_state_not_only_vault() -> None:
    """Regression test for a real bug found via live browser use: income
    is verified through the Revenue connector, never through the vault
    — the eligibility view must still show it VERIFIED afterward, not
    stay stuck on "not started" because it only ever checked documents."""
    client.post("/api/v1/demo/reset")
    client.post("/api/v1/demo/consent/income-certificate")
    client.post("/api/v1/demo/actions/submit-income-certificate")
    client.post("/api/v1/demo/actions/approve-income-certificate")

    catalog = client.get("/api/v1/demo/catalog").json()
    citizen_id = catalog["citizen_id"]

    eligibility = client.get(
        f"/api/v1/citizens/{citizen_id}/eligibility/college_admission_scholarship"
    ).json()
    income = next(
        s for s in eligibility["services"] if s["service_code"] == "income_certificate"
    )
    assert income["status"] == "verified"
    scholarship = next(
        s for s in eligibility["services"] if s["service_code"] == "education_scholarship"
    )
    assert scholarship["status"] == "ready"
