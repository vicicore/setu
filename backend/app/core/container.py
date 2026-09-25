"""Composition root. Every place in the codebase that needs a
repository, storage adapter, or connector asks here for one — never
constructs `LocalJsonApplicationRepository()` etc. directly. Adding a
Supabase-backed persistence_backend or an Appwrite storage_backend later
means adding one branch in each factory below; nothing that calls these
factories needs to change."""

from functools import lru_cache

from app.core.config import get_settings
from app.repositories.interfaces import (
    ApplicationRepository,
    AuditLogRepository,
    AuthRepository,
    CitizenRepository,
    ConnectorRequestRepository,
    DocumentRepository,
)
from app.repositories.local.application_repository import LocalJsonApplicationRepository
from app.repositories.local.audit_log_repository import LocalJsonAuditLogRepository
from app.repositories.local.auth_repository import LocalJsonAuthRepository
from app.repositories.local.citizen_repository import LocalJsonCitizenRepository
from app.repositories.local.connector_request_repository import LocalJsonConnectorRequestRepository
from app.repositories.local.document_repository import LocalJsonDocumentRepository
from app.services.connectors.base import GovernmentConnector
from app.services.connectors.education import EducationMockConnector
from app.services.connectors.finance import FinanceMockConnector
from app.services.connectors.home_affairs import HomeAffairsMockConnector
from app.services.connectors.labour import LabourMockConnector
from app.services.connectors.revenue import RevenueMockConnector
from app.services.connectors.social_justice import SocialJusticeMockConnector
from app.services.connectors.urban_development import UrbanDevelopmentMockConnector
from app.services.auth_service import AuthService
from app.services.document_service import DocumentVaultService
from app.services.citizen_service import CitizenProfileService
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
def get_connector_request_repository() -> ConnectorRequestRepository:
    settings = get_settings()
    if settings.persistence_backend == "local":
        return LocalJsonConnectorRequestRepository()
    raise NotImplementedError(
        f"persistence_backend={settings.persistence_backend!r} has no connector-request repository wired yet"
    )


@lru_cache
def get_revenue_connector() -> RevenueMockConnector:
    """Connectors are now stateless wrappers over
    ConnectorRequestRepository (Phase 7) — kept as cached singletons for
    consistency with the other factories here, not because correctness
    depends on it anymore; a fresh instance would behave identically
    since all request state lives in the repository, surviving restarts."""
    return RevenueMockConnector(get_connector_request_repository())


@lru_cache
def _connector_registry() -> dict[str, GovernmentConnector]:
    repo = get_connector_request_repository()
    return {
        "Revenue": get_revenue_connector(),
        "Higher Education": EducationMockConnector(repo),
        "Social Justice": SocialJusticeMockConnector(repo),
        "Labour": LabourMockConnector(repo),
        "Urban Development": UrbanDevelopmentMockConnector(repo),
        "Finance": FinanceMockConnector(repo),
        "Home": HomeAffairsMockConnector(repo),
    }


def get_connector_for_department(department: str) -> GovernmentConnector:
    """Generic resolution used by the non-demo journeys API, so a second
    life event (or a third) never needs orchestrator or API changes —
    only a department -> connector mapping entry here. The /demo route's
    hardcoded get_revenue_connector() above is untouched on purpose: it
    backs the already-approved, deterministic College Admission flow."""
    try:
        return _connector_registry()[department]
    except KeyError as exc:
        raise ValueError(f"No connector registered for department {department!r}") from exc


@lru_cache
def get_journey_service() -> JourneyService:
    return JourneyService(
        orchestrator=JourneyOrchestrator(),
        application_repo=get_application_repository(),
        audit_repo=get_audit_log_repository(),
    )


@lru_cache
def get_citizen_repository() -> CitizenRepository:
    settings = get_settings()
    if settings.persistence_backend == "local":
        return LocalJsonCitizenRepository()
    raise NotImplementedError(
        f"persistence_backend={settings.persistence_backend!r} has no citizen repository wired yet"
    )


@lru_cache
def get_document_repository() -> DocumentRepository:
    settings = get_settings()
    if settings.persistence_backend == "local":
        return LocalJsonDocumentRepository()
    raise NotImplementedError(
        f"persistence_backend={settings.persistence_backend!r} has no document repository wired yet"
    )


@lru_cache
def get_citizen_profile_service() -> CitizenProfileService:
    return CitizenProfileService(get_citizen_repository())


@lru_cache
def get_document_vault_service() -> DocumentVaultService:
    return DocumentVaultService(
        get_document_repository(), get_document_storage(), get_audit_log_repository()
    )


@lru_cache
def get_auth_repository() -> AuthRepository:
    settings = get_settings()
    if settings.persistence_backend == "local":
        return LocalJsonAuthRepository()
    raise NotImplementedError(
        f"persistence_backend={settings.persistence_backend!r} has no auth repository wired yet"
    )


@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(get_auth_repository())
