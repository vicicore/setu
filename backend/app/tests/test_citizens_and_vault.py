"""Citizen profile + document vault against the local repository/storage
adapters — CRUD only, deliberately not wired to Supabase/Appwrite yet.
Also exercises the security requirements the vault must enforce
regardless of backend: MIME allow-list and the 5MB limit. Every call is
authenticated (Phase 7) — see test_authorization.py for cross-citizen
isolation specifically."""

from fastapi.testclient import TestClient

from app.core.container import get_audit_log_repository
from app.main import app
from app.tests.conftest import login

client = TestClient(app)


def test_profile_not_found_before_creation() -> None:
    citizen_id, headers = login(client)
    response = client.get(f"/api/v1/citizens/{citizen_id}/profile", headers=headers)
    assert response.status_code == 404


def test_profile_requires_authentication() -> None:
    response = client.get("/api/v1/citizens/some-citizen/profile")
    assert response.status_code == 401


def test_profile_upsert_then_get_and_completeness_increases() -> None:
    citizen_id, headers = login(client)
    first = client.put(
        f"/api/v1/citizens/{citizen_id}/profile",
        json={"full_name": "Priya Deshmukh"},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["full_name"] == "Priya Deshmukh"
    low_completeness = first.json()["profile_completeness_pct"]

    second = client.put(
        f"/api/v1/citizens/{citizen_id}/profile",
        json={"district": "Pune", "taluka": "Haveli", "phone": "9800000000", "dob": "2004-05-01"},
        headers=headers,
    )
    assert second.status_code == 200
    body = second.json()
    assert body["full_name"] == "Priya Deshmukh"  # preserved from the first upsert
    assert body["district"] == "Pune"
    assert body["profile_completeness_pct"] > low_completeness

    fetched = client.get(f"/api/v1/citizens/{citizen_id}/profile", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["district"] == "Pune"


def test_document_upload_list_and_get() -> None:
    citizen_id, headers = login(client)
    upload = client.post(
        f"/api/v1/citizens/{citizen_id}/documents",
        data={"doc_type": "income_certificate", "issuer": "Revenue Department"},
        files={"file": ("income.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")},
        headers=headers,
    )
    assert upload.status_code == 201
    body = upload.json()
    assert body["doc_type"] == "income_certificate"
    assert body["status"] == "uploaded"
    assert body["url"].startswith("/media/documents/")

    listing = client.get(f"/api/v1/citizens/{citizen_id}/documents", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    fetched = client.get(f"/api/v1/citizens/{citizen_id}/documents/{body['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["original_filename"] == "income.pdf"


def test_document_upload_rejects_disallowed_mime_type() -> None:
    citizen_id, headers = login(client)
    response = client.post(
        f"/api/v1/citizens/{citizen_id}/documents",
        data={"doc_type": "income_certificate"},
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/x-msdownload")},
        headers=headers,
    )
    assert response.status_code == 422


def test_document_upload_rejects_oversized_file() -> None:
    citizen_id, headers = login(client)
    oversized = b"0" * (6 * 1024 * 1024)  # 6MB > 5MB limit
    response = client.post(
        f"/api/v1/citizens/{citizen_id}/documents",
        data={"doc_type": "income_certificate"},
        files={"file": ("big.pdf", oversized, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 422


def test_document_lifecycle_is_audited_even_without_an_active_journey() -> None:
    """Regression test: JourneyService's audit trail is application-
    scoped, so a document with no journey requiring its doc_type used
    to leave upload/review/verify completely unaudited. DocumentVaultService
    now audits its own transitions independently of journey cascades."""
    citizen_id, headers = login(client)
    upload = client.post(
        f"/api/v1/citizens/{citizen_id}/documents",
        data={"doc_type": "supplementary_document"},
        files={"file": ("extra.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=headers,
    )
    document_id = upload.json()["id"]
    client.post(
        f"/api/v1/citizens/{citizen_id}/documents/{document_id}/submit-for-review", headers=headers
    )
    client.post(f"/api/v1/citizens/{citizen_id}/documents/{document_id}/verify", headers=headers)

    entries = get_audit_log_repository().list_all()
    actions_for_doc = {e.action for e in entries if e.resource_id == document_id}
    assert actions_for_doc == {
        "document.uploaded",
        "document.submitted_for_review",
        "document.verified",
    }
    assert all(e.application_id is None for e in entries if e.resource_id == document_id)
