from app.core.config import get_settings
from app.repositories.interfaces import DocumentRepository
from app.repositories.local.json_file_store import JsonFileStore
from app.repositories.models import DocumentRecord


class LocalJsonDocumentRepository(DocumentRepository):
    def __init__(self, data_dir: str | None = None) -> None:
        settings = get_settings()
        base = data_dir or settings.local_data_dir
        self._store = JsonFileStore(f"{base}/documents.json", default={})

    def create(self, record: DocumentRecord) -> DocumentRecord:
        payload = record.model_dump(mode="json")

        def _mutate(data: dict) -> dict:
            data[record.id] = payload
            return data

        self._store.mutate(_mutate)
        return record

    def get(self, document_id: str) -> DocumentRecord | None:
        data = self._store.read() or {}
        raw = data.get(document_id)
        return DocumentRecord.model_validate(raw) if raw else None

    def list_for_citizen(self, citizen_id: str) -> list[DocumentRecord]:
        data = self._store.read() or {}
        return [
            DocumentRecord.model_validate(raw)
            for raw in data.values()
            if raw.get("citizen_id") == citizen_id
        ]

    def delete(self, document_id: str) -> None:
        def _mutate(data: dict) -> dict:
            data.pop(document_id, None)
            return data

        self._store.mutate(_mutate)
