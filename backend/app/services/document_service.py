from datetime import datetime, timezone

from app.repositories.interfaces import AuditLogRepository, DocumentRepository
from app.repositories.models import AuditLogEntry, DocumentRecord
from app.schemas.enums import DocumentStatus
from app.storage.interfaces import DocumentStoragePort


class DocumentNotFoundError(ValueError):
    pass


class InvalidDocumentTransitionError(ValueError):
    pass


class DocumentVaultService:
    """Document service -> storage interface -> local/demo implementation
    today, Appwrite later (Master Prompt section 4E). Metadata (who owns
    it, what type, verification status) lives in DocumentRepository; the
    file bytes live behind DocumentStoragePort — two different concerns,
    two different ports, deliberately not conflated into one.

    Also the one place that audits document lifecycle transitions
    (upload/submit-for-review/verify/reject) — these must be recorded
    even when a document has no active journey to cascade into, which
    JourneyService's own audit trail (application-scoped) cannot cover."""

    def __init__(
        self, document_repo: DocumentRepository, storage: DocumentStoragePort, audit_repo: AuditLogRepository
    ) -> None:
        self._documents = document_repo
        self._storage = storage
        self._audit = audit_repo

    def _audit_event(self, record: DocumentRecord, action: str, metadata: dict) -> None:
        self._audit.append(
            AuditLogEntry(
                actor="citizen",
                action=action,
                resource_type="document",
                resource_id=record.id,
                metadata={"citizen_id": record.citizen_id, "doc_type": record.doc_type, **metadata},
                created_at=datetime.now(timezone.utc),
            )
        )

    def upload(
        self,
        citizen_id: str,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        doc_type: str,
        issuer: str | None,
    ) -> DocumentRecord:
        stored = self._storage.save(file_bytes, filename, mime_type)
        now = datetime.now(timezone.utc)
        record = DocumentRecord(
            citizen_id=citizen_id,
            doc_type=doc_type,
            issuer=issuer,
            storage_key=stored.storage_key,
            original_filename=stored.original_filename,
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            created_at=now,
            updated_at=now,
        )
        created = self._documents.create(record)
        self._audit_event(created, "document.uploaded", {"original_filename": stored.original_filename})
        return created

    def list_for_citizen(self, citizen_id: str) -> list[DocumentRecord]:
        return self._documents.list_for_citizen(citizen_id)

    def get(self, document_id: str) -> DocumentRecord:
        record = self._documents.get(document_id)
        if record is None:
            raise DocumentNotFoundError(f"No document found with id {document_id}")
        return record

    def get_url(self, record: DocumentRecord) -> str:
        return self._storage.get_url(record.storage_key)

    def delete(self, document_id: str) -> None:
        record = self.get(document_id)
        self._storage.delete(record.storage_key)
        self._documents.delete(document_id)

    def submit_for_review(self, document_id: str) -> DocumentRecord:
        """UPLOADED -> UNDER_REVIEW. A document sitting in the vault is
        not automatically equivalent to being verified — this is the
        first real transition of that lifecycle."""
        record = self.get(document_id)
        if record.status != DocumentStatus.UPLOADED:
            raise InvalidDocumentTransitionError(
                f"Cannot submit for review from status {record.status}"
            )
        record.status = DocumentStatus.UNDER_REVIEW
        record.updated_at = datetime.now(timezone.utc)
        saved = self._documents.save(record)
        self._audit_event(saved, "document.submitted_for_review", {})
        return saved

    def verify(self, document_id: str) -> DocumentRecord:
        """UNDER_REVIEW -> VERIFIED. For the demo this is simulated
        (there is no real department reviewer), but the transition
        itself is real, persisted backend state — see
        app/services/vault_integration.py for how this cascades into
        eligibility and any active journey."""
        record = self.get(document_id)
        if record.status != DocumentStatus.UNDER_REVIEW:
            raise InvalidDocumentTransitionError(
                f"Cannot verify from status {record.status}"
            )
        record.status = DocumentStatus.VERIFIED
        record.rejection_reason = None
        record.updated_at = datetime.now(timezone.utc)
        saved = self._documents.save(record)
        self._audit_event(saved, "document.verified", {})
        return saved

    def reject(self, document_id: str, reason: str) -> DocumentRecord:
        record = self.get(document_id)
        if record.status != DocumentStatus.UNDER_REVIEW:
            raise InvalidDocumentTransitionError(
                f"Cannot reject from status {record.status}"
            )
        record.status = DocumentStatus.REJECTED
        record.rejection_reason = reason
        record.updated_at = datetime.now(timezone.utc)
        saved = self._documents.save(record)
        self._audit_event(saved, "document.rejected", {"reason": reason})
        return saved
