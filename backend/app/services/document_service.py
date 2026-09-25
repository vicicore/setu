from datetime import datetime, timezone

from app.repositories.interfaces import DocumentRepository
from app.repositories.models import DocumentRecord
from app.storage.interfaces import DocumentStoragePort


class DocumentNotFoundError(ValueError):
    pass


class DocumentVaultService:
    """Document service -> storage interface -> local/demo implementation
    today, Appwrite later (Master Prompt section 4E). Metadata (who owns
    it, what type, verification status) lives in DocumentRepository; the
    file bytes live behind DocumentStoragePort — two different concerns,
    two different ports, deliberately not conflated into one."""

    def __init__(self, document_repo: DocumentRepository, storage: DocumentStoragePort) -> None:
        self._documents = document_repo
        self._storage = storage

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
        record = DocumentRecord(
            citizen_id=citizen_id,
            doc_type=doc_type,
            issuer=issuer,
            storage_key=stored.storage_key,
            original_filename=stored.original_filename,
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            created_at=datetime.now(timezone.utc),
        )
        return self._documents.create(record)

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
