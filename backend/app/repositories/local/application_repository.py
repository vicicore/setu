from app.core.config import get_settings
from app.repositories.interfaces import ApplicationRepository
from app.repositories.local.json_file_store import JsonFileStore
from app.repositories.models import ApplicationRecord


class LocalJsonApplicationRepository(ApplicationRepository):
    def __init__(self, data_dir: str | None = None) -> None:
        settings = get_settings()
        base = data_dir or settings.local_data_dir
        self._store = JsonFileStore(f"{base}/applications.json", default={})

    def create(self, record: ApplicationRecord) -> ApplicationRecord:
        payload = record.model_dump(mode="json")

        def _mutate(data: dict) -> dict:
            data[record.id] = payload
            return data

        self._store.mutate(_mutate)
        return record

    def get(self, application_id: str) -> ApplicationRecord | None:
        data = self._store.read() or {}
        raw = data.get(application_id)
        return ApplicationRecord.model_validate(raw) if raw else None

    def save(self, record: ApplicationRecord) -> ApplicationRecord:
        payload = record.model_dump(mode="json")

        def _mutate(data: dict) -> dict:
            data[record.id] = payload
            return data

        self._store.mutate(_mutate)
        return record

    def delete(self, application_id: str) -> None:
        def _mutate(data: dict) -> dict:
            data.pop(application_id, None)
            return data

        self._store.mutate(_mutate)

    def list_for_citizen(self, citizen_id: str) -> list[ApplicationRecord]:
        data = self._store.read() or {}
        return [
            ApplicationRecord.model_validate(raw)
            for raw in data.values()
            if raw.get("citizen_id") == citizen_id
        ]

    def list_all(self) -> list[ApplicationRecord]:
        data = self._store.read() or {}
        return [ApplicationRecord.model_validate(raw) for raw in data.values()]
