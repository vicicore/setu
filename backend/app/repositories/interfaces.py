"""Repository ports. Anything above this line (API routes, the service
layer, JourneyOrchestrator) depends only on these interfaces — never on
a concrete storage technology. A Supabase-backed implementation is added
later by writing a new class that satisfies the same contract; nothing
above this line changes."""

from abc import ABC, abstractmethod

from app.repositories.models import (
    ApplicationRecord,
    AuditLogEntry,
    CitizenProfileRecord,
    DocumentRecord,
)


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

    @abstractmethod
    def find_by_step_external_reference(
        self, external_reference: str
    ) -> tuple[ApplicationRecord, str] | None:
        """Returns (record, service_code) for the step carrying this
        connector external_reference, or None. This is how a webhook —
        which only knows the reference a connector handed out — is
        routed back to the right application/step without the caller
        needing to know the application id up front."""
        ...


class AuditLogRepository(ABC):
    @abstractmethod
    def append(self, entry: AuditLogEntry) -> AuditLogEntry: ...

    @abstractmethod
    def list_for_application(self, application_id: str) -> list[AuditLogEntry]: ...

    @abstractmethod
    def list_all(self, limit: int = 100) -> list[AuditLogEntry]: ...


class CitizenRepository(ABC):
    @abstractmethod
    def get(self, citizen_id: str) -> CitizenProfileRecord | None: ...

    @abstractmethod
    def upsert(self, record: CitizenProfileRecord) -> CitizenProfileRecord: ...


class DocumentRepository(ABC):
    @abstractmethod
    def create(self, record: DocumentRecord) -> DocumentRecord: ...

    @abstractmethod
    def get(self, document_id: str) -> DocumentRecord | None: ...

    @abstractmethod
    def list_for_citizen(self, citizen_id: str) -> list[DocumentRecord]: ...

    @abstractmethod
    def delete(self, document_id: str) -> None: ...
