"""Phase 7 priority 3: citizens must not be able to reach each other's
data by editing a citizen_id or application_id in a URL. Every one of
these must fail with 401 (no session) or 403/404 (wrong session) — never
200. This is what proves authorization is enforced server-side, not by
the frontend hiding a button."""

from fastapi.testclient import TestClient

from app.main import app
from app.tests.conftest import login

client = TestClient(app)


def _start_journey(citizen_id: str, headers: dict) -> str:
    started = client.post(
        f"/api/v1/citizens/{citizen_id}/journeys",
        json={"life_event_code": "start_small_business"},
        headers=headers,
    )
    assert started.status_code == 201
    return started.json()["application_id"]


def _upload_document(citizen_id: str, headers: dict) -> str:
    upload = client.post(
        f"/api/v1/citizens/{citizen_id}/documents",
        data={"doc_type": "identity_verification"},
        files={"file": ("id.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=headers,
    )
    assert upload.status_code == 201
    return upload.json()["id"]


def test_citizen_cannot_read_or_write_another_citizens_profile() -> None:
    citizen_a, headers_a = login(client)
    citizen_b, headers_b = login(client)
    client.put(f"/api/v1/citizens/{citizen_b}/profile", json={"full_name": "B"}, headers=headers_b)

    assert client.get(f"/api/v1/citizens/{citizen_b}/profile", headers=headers_a).status_code == 403
    assert (
        client.put(
            f"/api/v1/citizens/{citizen_b}/profile", json={"full_name": "Hijacked"}, headers=headers_a
        ).status_code
        == 403
    )
    # Unauthenticated is also rejected, not just cross-citizen.
    assert client.get(f"/api/v1/citizens/{citizen_b}/profile").status_code == 401


def test_citizen_cannot_list_or_read_another_citizens_documents() -> None:
    citizen_a, headers_a = login(client)
    citizen_b, headers_b = login(client)
    document_id = _upload_document(citizen_b, headers_b)

    assert client.get(f"/api/v1/citizens/{citizen_b}/documents", headers=headers_a).status_code == 403
    assert (
        client.get(
            f"/api/v1/citizens/{citizen_b}/documents/{document_id}", headers=headers_a
        ).status_code
        == 403
    )
    # Even naming citizen A's own id in the URL doesn't launder access to
    # a document that actually belongs to citizen B.
    assert (
        client.get(
            f"/api/v1/citizens/{citizen_a}/documents/{document_id}", headers=headers_a
        ).status_code
        == 404
    )


def test_citizen_cannot_upload_or_transition_another_citizens_documents() -> None:
    citizen_a, headers_a = login(client)
    citizen_b, headers_b = login(client)
    document_id = _upload_document(citizen_b, headers_b)

    upload_as_a_for_b = client.post(
        f"/api/v1/citizens/{citizen_b}/documents",
        data={"doc_type": "identity_verification"},
        files={"file": ("id.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=headers_a,
    )
    assert upload_as_a_for_b.status_code == 403

    for path in (
        f"/api/v1/citizens/{citizen_b}/documents/{document_id}/submit-for-review",
        f"/api/v1/citizens/{citizen_b}/documents/{document_id}/verify",
    ):
        assert client.post(path, headers=headers_a).status_code == 403
    assert (
        client.post(
            f"/api/v1/citizens/{citizen_b}/documents/{document_id}/reject",
            json={"reason": "not yours to reject"},
            headers=headers_a,
        ).status_code
        == 403
    )


def test_citizen_cannot_list_or_start_journeys_for_another_citizen() -> None:
    citizen_a, headers_a = login(client)
    citizen_b, headers_b = login(client)

    assert client.get(f"/api/v1/citizens/{citizen_b}/journeys", headers=headers_a).status_code == 403
    assert (
        client.post(
            f"/api/v1/citizens/{citizen_b}/journeys",
            json={"life_event_code": "start_small_business"},
            headers=headers_a,
        ).status_code
        == 403
    )


def test_citizen_cannot_read_or_act_on_another_citizens_journey() -> None:
    citizen_a, headers_a = login(client)
    citizen_b, headers_b = login(client)
    application_id = _start_journey(citizen_b, headers_b)

    assert client.get(f"/api/v1/journeys/{application_id}", headers=headers_a).status_code == 403
    assert (
        client.post(
            f"/api/v1/journeys/{application_id}/consent/business_registration",
            json={"purpose": "steal it"},
            headers=headers_a,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/journeys/{application_id}/consent/business_registration/revoke",
            headers=headers_a,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/journeys/{application_id}/submit/business_registration",
            json={},
            headers=headers_a,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/journeys/{application_id}/approve/business_registration", headers=headers_a
        ).status_code
        == 403
    )
    # Unauthenticated is rejected outright, before ownership is even checked.
    assert client.get(f"/api/v1/journeys/{application_id}").status_code == 401


def test_citizen_cannot_read_another_citizens_eligibility() -> None:
    citizen_a, headers_a = login(client)
    citizen_b, _headers_b = login(client)

    response = client.get(
        f"/api/v1/citizens/{citizen_b}/eligibility/college_admission_scholarship", headers=headers_a
    )
    assert response.status_code == 403


def test_admin_session_can_access_any_citizens_data() -> None:
    """require_owner_or_admin's other branch: an admin session is not
    subject to the same-citizen restriction — proven here so the two
    behaviors (owner OR admin) are both actually exercised."""
    citizen_b, headers_b = login(client)
    client.put(f"/api/v1/citizens/{citizen_b}/profile", json={"full_name": "B"}, headers=headers_b)
    _admin_id, admin_headers = login(client, identifier="admin")

    response = client.get(f"/api/v1/citizens/{citizen_b}/profile", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "B"
