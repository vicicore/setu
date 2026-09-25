"""Citizen profile + document vault against the local repository/storage
adapters (Phase 4 priority 4) — CRUD only, deliberately not wired to
Supabase/Appwrite yet. Also exercises the security requirements the vault
must enforce regardless of backend: MIME allow-list and the 5MB limit."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_profile_not_found_before_creation() -> None:
    response = client.get("/api/v1/citizens/citizen-test-1/profile")
    assert response.status_code == 404


def test_profile_upsert_then_get_and_completeness_increases() -> None:
    first = client.put(
        "/api/v1/citizens/citizen-test-1/profile",
        json={"full_name": "Priya Deshmukh"},
    )
    assert first.status_code == 200
    assert first.json()["full_name"] == "Priya Deshmukh"
    low_completeness = first.json()["profile_completeness_pct"]

    second = client.put(
        "/api/v1/citizens/citizen-test-1/profile",
        json={"district": "Pune", "taluka": "Haveli", "phone": "9800000000", "dob": "2004-05-01"},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["full_name"] == "Priya Deshmukh"  # preserved from the first upsert
    assert body["district"] == "Pune"
    assert body["profile_completeness_pct"] > low_completeness

    fetched = client.get("/api/v1/citizens/citizen-test-1/profile")
    assert fetched.status_code == 200
    assert fetched.json()["district"] == "Pune"


def test_document_upload_list_and_get() -> None:
    upload = client.post(
        "/api/v1/citizens/citizen-test-2/documents",
        data={"doc_type": "income_certificate", "issuer": "Revenue Department"},
        files={"file": ("income.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")},
    )
    assert upload.status_code == 201
    body = upload.json()
    assert body["doc_type"] == "income_certificate"
    assert body["status"] == "pending"
    assert body["url"].startswith("/media/documents/")

    listing = client.get("/api/v1/citizens/citizen-test-2/documents")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    fetched = client.get(f"/api/v1/citizens/citizen-test-2/documents/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["original_filename"] == "income.pdf"


def test_document_upload_rejects_disallowed_mime_type() -> None:
    response = client.post(
        "/api/v1/citizens/citizen-test-3/documents",
        data={"doc_type": "income_certificate"},
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/x-msdownload")},
    )
    assert response.status_code == 422


def test_document_upload_rejects_oversized_file() -> None:
    oversized = b"0" * (6 * 1024 * 1024)  # 6MB > 5MB limit
    response = client.post(
        "/api/v1/citizens/citizen-test-4/documents",
        data={"doc_type": "income_certificate"},
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 422


def test_document_not_found_for_wrong_citizen() -> None:
    upload = client.post(
        "/api/v1/citizens/citizen-owner/documents",
        data={"doc_type": "domicile_certificate"},
        files={"file": ("domicile.png", b"\x89PNG fake", "image/png")},
    )
    document_id = upload.json()["id"]

    response = client.get(f"/api/v1/citizens/someone-else/documents/{document_id}")
    assert response.status_code == 404
