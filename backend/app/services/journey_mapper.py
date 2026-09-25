"""Converts between the in-memory domain Journey (what JourneyOrchestrator
operates on — carries a live DependencyGraph) and the serializable
ApplicationRecord (what a repository persists). This is the seam that
keeps the orchestrator storage-agnostic: it never sees an
ApplicationRecord, and no repository ever sees a DependencyGraph."""

from datetime import datetime, timezone

from app.repositories.models import ApplicationRecord, ConsentRecord, StepRecord
from app.services.dependency_graph import get_graph
from app.services.orchestrator import Consent, Journey, JourneyStep


def to_record(journey: Journey, created_at: datetime | None = None) -> ApplicationRecord:
    now = datetime.now(timezone.utc)
    return ApplicationRecord(
        id=journey.id,
        citizen_id=journey.citizen_id,
        life_event_code=journey.life_event_code,
        steps={
            code: StepRecord(
                service_code=step.service_code,
                status=step.status,
                blocked_reason=step.blocked_reason,
                external_reference=step.external_reference,
                submitted_at=step.submitted_at,
                sla_due_at=step.sla_due_at,
                updated_at=step.updated_at,
            )
            for code, step in journey.steps.items()
        },
        consents={
            code: ConsentRecord(
                service_code=c.service_code,
                recipient_department=c.recipient_department,
                purpose=c.purpose,
                granted_at=c.granted_at,
                expires_at=c.expires_at,
                revoked_at=c.revoked_at,
            )
            for code, c in journey.consents.items()
        },
        timeline=list(journey.timeline),
        created_at=created_at or now,
        updated_at=now,
    )


def to_domain(record: ApplicationRecord) -> Journey:
    graph = get_graph(record.life_event_code)
    return Journey(
        id=record.id,
        citizen_id=record.citizen_id,
        life_event_code=record.life_event_code,
        graph=graph,
        steps={
            code: JourneyStep(
                service_code=s.service_code,
                status=s.status,
                blocked_reason=s.blocked_reason,
                external_reference=s.external_reference,
                submitted_at=s.submitted_at,
                sla_due_at=s.sla_due_at,
                updated_at=s.updated_at,
            )
            for code, s in record.steps.items()
        },
        consents={
            code: Consent(
                service_code=c.service_code,
                recipient_department=c.recipient_department,
                purpose=c.purpose,
                granted_at=c.granted_at,
                expires_at=c.expires_at,
                revoked_at=c.revoked_at,
            )
            for code, c in record.consents.items()
        },
        timeline=list(record.timeline),
    )
