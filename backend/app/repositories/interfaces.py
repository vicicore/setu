"""Repository ports. Anything above this line (API routes, the service
layer, JourneyOrchestrator) depends only on these interfaces — never on
a concrete storage technology. A Supabase-backed implementation is added
later by writing a new class that satisfies the same contract; nothing
above this line changes."""

from abc import ABC, abstractmethod

from app.repositories.models import ApplicationRecord, AuditLogEntry


class ApplicationRepository(ABC):
    @abstractmethod
    def create(self, record: ApplicationRecord) -> ApplicationRecord: ...

    @abstractmethod
    def get(self, application_id: str) -> ApplicationRecord | None: ...

    @abstractmethod
    def save(self, record: ApplicationRecord) -> ApplicationRecord: ...

    @abstractmethod
    def delete(self, application_id: str) -> None: ...

    @abstractmethod
    def list_for_citizen(self, citizen_id: str) -> list[ApplicationRecord]: ...

    @abstractmethod
    def list_all(self) -> list[ApplicationRecord]: ...


class AuditLogRepository(ABC):
    @abstractmethod
    def append(self, entry: AuditLogEntry) -> AuditLogEntry: ...

    @abstractmethod
    def list_for_application(self, application_id: str) -> list[AuditLogEntry]: ...

    @abstractmethod
    def list_all(self, limit: int = 100) -> list[AuditLogEntry]: ...
