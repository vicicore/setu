from app.core.config import get_settings
from app.repositories.interfaces import ConnectorRequestRepository
from app.repositories.local.json_file_store import JsonFileStore
from app.repositories.models import ConnectorRequestRecord


class LocalJsonConnectorRequestRepository(ConnectorRequestRepository):
    def __init__(self, data_dir: str | None = None) -> None:
        settings = get_settings()
        base = data_dir or settings.local_data_dir
        self._store = JsonFileStore(f"{base}/connector_requests.json", default={})

    def save(self, record: ConnectorRequestRecord) -> ConnectorRequestRecord:
        payload = record.model_dump(mode="json")

        def _mutate(data: dict) -> dict:
            data[record.external_reference] = payload
            return data

        self._store.mutate(_mutate)
        return record

    def get(self, external_reference: str) -> ConnectorRequestRecord | None:
        data = self._store.read() or {}
        raw = data.get(external_reference)
        return ConnectorRequestRecord.model_validate(raw) if raw else None
