from app.core.config import get_settings
from app.repositories.interfaces import AuthRepository
from app.repositories.local.json_file_store import JsonFileStore
from app.repositories.models import AccountRecord, SessionRecord


class LocalJsonAuthRepository(AuthRepository):
    def __init__(self, data_dir: str | None = None) -> None:
        settings = get_settings()
        base = data_dir or settings.local_data_dir
        self._accounts = JsonFileStore(f"{base}/accounts.json", default={})
        self._sessions = JsonFileStore(f"{base}/sessions.json", default={})

    def get_account_by_identifier(self, identifier: str) -> AccountRecord | None:
        data = self._accounts.read() or {}
        raw = data.get(identifier)
        return AccountRecord.model_validate(raw) if raw else None

    def create_account(self, record: AccountRecord) -> AccountRecord:
        payload = record.model_dump(mode="json")

        def _mutate(data: dict) -> dict:
            data[record.identifier] = payload
            return data

        self._accounts.mutate(_mutate)
        return record

    def create_session(self, record: SessionRecord) -> SessionRecord:
        payload = record.model_dump(mode="json")

        def _mutate(data: dict) -> dict:
            data[record.token] = payload
            return data

        self._sessions.mutate(_mutate)
        return record

    def get_session(self, token: str) -> SessionRecord | None:
        data = self._sessions.read() or {}
        raw = data.get(token)
        return SessionRecord.model_validate(raw) if raw else None

    def delete_session(self, token: str) -> None:
        def _mutate(data: dict) -> dict:
            data.pop(token, None)
            return data

        self._sessions.mutate(_mutate)
