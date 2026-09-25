"""Composition root. Every place in the codebase that needs a
repository, storage adapter, or connector asks here for one — never
constructs `LocalJsonApplicationRepository()` etc. directly. Adding a
Supabase-backed persistence_backend or an Appwrite storage_backend later
means adding one branch in each factory below; nothing that calls these
factories needs to change."""

from functools import lru_cache

from app.core.config import get_settings
from app.repositories.interfaces import ApplicationRepository, AuditLogRepository
from app.repositories.local.application_repository import LocalJsonApplicationRepository
from app.repositories.local.audit_log_repository import LocalJsonAuditLogRepository
from app.services.connectors.revenue import RevenueMockConnector
from app.services.journey_service import JourneyService
from app.services.orchestrator import JourneyOrchestrator
from app.storage.interfaces import DocumentStoragePort
from app.storage.local_disk import LocalDiskDocumentStorage


@lru_cache
def get_application_repository() -> ApplicationRepository:
    settings = get_settings()
    if settings.persistence_backend == "local":
        return LocalJsonApplicationRepository()
    raise NotImplementedError(
        f"persistence_backend={settings.persistence_backend!r} has no repository wired yet"
    )


@lru_cache
def get_audit_log_repository() -> AuditLogRepository:
    settings = get_settings()
    if settings.persistence_backend == "local":
        return LocalJsonAuditLogRepository()
    raise NotImplementedError(
        f"persistence_backend={settings.persistence_backend!r} has no audit repository wired yet"
    )


@lru_cache
def get_document_storage() -> DocumentStoragePort:
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalDiskDocumentStorage()
    raise NotImplementedError(
        f"storage_backend={settings.storage_backend!r} has no storage adapter wired yet"
    )


@lru_cache
def get_revenue_connector() -> RevenueMockConnector:
    """Connector instances hold live request state (department system of
    record, in production). For the demo they're process-wide singletons
    so an approval simulated later in the same run can find the request
    a submit created earlier — this is a demo-scope simplification, not
    a persistence guarantee; see docs/DECISIONS.md."""
    return RevenueMockConnector()


@lru_cache
def get_journey_service() -> JourneyService:
    return JourneyService(
        orchestrator=JourneyOrchestrator(),
        application_repo=get_application_repository(),
        audit_repo=get_audit_log_repository(),
    )
