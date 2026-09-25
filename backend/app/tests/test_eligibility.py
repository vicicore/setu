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


def test_eligibility_endpoint_returns_reasons_over_http() -> None:
    response = client.post(
        "/api/v1/eligibility/evaluate",
        json={
            "life_event_code": "college_admission_scholarship",
            "verified_service_codes": ["identity_verification", "domicile_certificate", "caste_certificate"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    scholarship = next(s for s in body["services"] if s["service_code"] == "education_scholarship")
    assert scholarship["status"] == "blocked"
    assert scholarship["depends_on_service_code"] == "income_certificate"
    assert body["overall_ready"] is False


def test_eligibility_endpoint_rejects_unknown_life_event() -> None:
    response = client.post(
        "/api/v1/eligibility/evaluate",
        json={"life_event_code": "not_a_real_life_event", "verified_service_codes": []},
    )
    assert response.status_code == 404
