"""The service layer: UI/API -> here -> JourneyOrchestrator (business
logic) + repositories (persistence). Nothing in JourneyOrchestrator
knows a repository exists; nothing in a repository knows what a
Consent or a DependencyGraph is. This module is the only place that
talks to both."""

from datetime import datetime, timezone

from app.repositories.interfaces import ApplicationRepository, AuditLogRepository
from app.repositories.models import ApplicationRecord, AuditLogEntry
from app.services.connectors.base import GovernmentConnector
from app.services.dependency_graph import DependencyGraph
from app.services.journey_mapper import to_domain, to_record
from app.services.orchestrator import Journey, JourneyOrchestrator


class JourneyService:
    def __init__(
        self,
        orchestrator: JourneyOrchestrator,
        application_repo: ApplicationRepository,
        audit_repo: AuditLogRepository,
    ) -> None:
        self._orchestrator = orchestrator
        self._applications = application_repo
        self._audit = audit_repo

    def _audit_event(self, application_id: str, actor: str, action: str, metadata: dict) -> None:
        self._audit.append(
            AuditLogEntry(
                application_id=application_id,
                actor=actor,
                action=action,
                resource_type="application",
                resource_id=application_id,
                metadata=metadata,
                created_at=datetime.now(timezone.utc),
            )
        )

    def get_journey(self, application_id: str) -> Journey | None:
        record = self._applications.get(application_id)
        return to_domain(record) if record else None

    def start_or_reset_journey(
        self,
        application_id: str,
        citizen_id: str,
        life_event_code: str,
        graph: DependencyGraph,
        already_verified_service_codes: set[str],
    ) -> Journey:
        existing = self._applications.get(application_id)
        created_at = existing.created_at if existing else None

        journey = self._orchestrator.start_journey(
            citizen_id=citizen_id,
            life_event_code=life_event_code,
            graph=graph,
            already_verified_service_codes=already_verified_service_codes,
            journey_id=application_id,
        )
        record = to_record(journey, created_at=created_at)
        self._applications.save(record)
        self._audit_event(
            application_id, actor="citizen", action="journey.reset",
            metadata={"life_event_code": life_event_code},
        )
        return journey

    def grant_consent(self, application_id: str, service_code: str, purpose: str) -> Journey:
        record = self._require_record(application_id)
        journey = to_domain(record)
        self._orchestrator.grant_consent(journey, service_code, purpose=purpose)
        self._applications.save(to_record(journey, created_at=record.created_at))
        self._audit_event(
            application_id, actor="citizen", action="consent.granted",
            metadata={"service_code": service_code, "purpose": purpose},
        )
        return journey

    def submit_to_connector(
        self,
        application_id: str,
        service_code: str,
        connector: GovernmentConnector,
        payload: dict,
    ) -> Journey:
        record = self._require_record(application_id)
        journey = to_domain(record)
        external_reference = self._orchestrator.submit_to_connector(
            journey, service_code, connector, payload
        )
        self._applications.save(to_record(journey, created_at=record.created_at))
        self._audit_event(
            application_id, actor="citizen", action="connector.submitted",
            metadata={
                "service_code": service_code,
                "department": connector.department,
                "external_reference": external_reference,
            },
        )
        return journey

    def receive_connector_event(
        self, application_id: str, service_code: str, event_status: str
    ) -> Journey:
        record = self._require_record(application_id)
        journey = to_domain(record)
        changed = self._orchestrator.receive_connector_event(journey, service_code, event_status)
        self._applications.save(to_record(journey, created_at=record.created_at))
        self._audit_event(
            application_id, actor="system", action="connector.event_received",
            metadata={
                "service_code": service_code,
                "event_status": event_status,
                "cascaded_to": [c for c in changed if c != service_code],
            },
        )
        return journey

    def audit_trail(self, application_id: str) -> list[AuditLogEntry]:
        return self._audit.list_for_application(application_id)

    def _require_record(self, application_id: str) -> ApplicationRecord:
        record = self._applications.get(application_id)
        if record is None:
            raise ValueError(f"No application found with id {application_id}")
        return record
