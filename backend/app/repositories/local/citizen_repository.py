from app.core.config import get_settings
from app.repositories.interfaces import CitizenRepository
from app.repositories.local.json_file_store import JsonFileStore
from app.repositories.models import CitizenProfileRecord


class LocalJsonCitizenRepository(CitizenRepository):
    def __init__(self, data_dir: str | None = None) -> None:
        settings = get_settings()
        base = data_dir or settings.local_data_dir
        self._store = JsonFileStore(f"{base}/citizens.json", default={})

    def get(self, citizen_id: str) -> CitizenProfileRecord | None:
        data = self._store.read() or {}
        raw = data.get(citizen_id)
        return CitizenProfileRecord.model_validate(raw) if raw else None

    def upsert(self, record: CitizenProfileRecord) -> CitizenProfileRecord:
        payload = record.model_dump(mode="json")

        def _mutate(data: dict) -> dict:
            data[record.citizen_id] = payload
            return data

        self._store.mutate(_mutate)
        return record
