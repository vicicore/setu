"""Coordinates two services that must not know about each other
directly: DocumentVaultService (owns the document lifecycle) and
JourneyService (owns journey state). Verifying a document is a vault
concern; deciding what that means for an in-progress journey is an
orchestration concern — this module is the seam between them, so
neither service grows a dependency on the other."""

from app.repositories.models import DocumentRecord
from app.services.document_service import DocumentVaultService
from app.services.journey_service import JourneyService
from app.services.orchestrator import Journey


def verify_document_and_sync_journeys(
    document_id: str,
    vault: DocumentVaultService,
    journeys: JourneyService,
) -> tuple[DocumentRecord, list[Journey]]:
    record = vault.verify(document_id)
    updated = journeys.sync_verified_document(record.citizen_id, record.doc_type)
    return record, updated


def reject_document_and_sync_journeys(
    document_id: str,
    reason: str,
    vault: DocumentVaultService,
    journeys: JourneyService,
) -> tuple[DocumentRecord, list[Journey]]:
    record = vault.reject(document_id, reason)
    updated = journeys.sync_rejected_document(record.citizen_id, record.doc_type)
    return record, updated
