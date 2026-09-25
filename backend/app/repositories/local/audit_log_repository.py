from app.core.config import get_settings
from app.repositories.interfaces import AuditLogRepository
from app.repositories.local.json_file_store import JsonFileStore
from app.repositories.models import AuditLogEntry


class LocalJsonAuditLogRepository(AuditLogRepository):
    def __init__(self, data_dir: str | None = None) -> None:
        settings = get_settings()
        base = data_dir or settings.local_data_dir
        self._store = JsonFileStore(f"{base}/audit_log.json", default=[])

    def append(self, entry: AuditLogEntry) -> AuditLogEntry:
        payload = entry.model_dump(mode="json")

        def _mutate(data: list) -> list:
            data.append(payload)
            return data

        self._store.mutate(_mutate)
        return entry

    def list_for_application(self, application_id: str) -> list[AuditLogEntry]:
        data = self._store.read() or []
        return [
            AuditLogEntry.model_validate(raw)
            for raw in data
            if raw.get("application_id") == application_id
        ]

    def list_all(self, limit: int = 100) -> list[AuditLogEntry]:
        data = self._store.read() or []
        return [AuditLogEntry.model_validate(raw) for raw in data[-limit:]]
