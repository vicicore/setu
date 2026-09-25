"""Metrics computed directly from persisted application state — no
separately-tracked counters, no decorative placeholder numbers. Every
figure here is derived by walking real ApplicationRecords through the
same DependencyGraph/SLA logic the rest of the system uses, so it can
never drift from what a citizen or judge sees in /demo. This is
groundwork for the eventual admin dashboard (Master Prompt section 4L)
— an API to build a UI against, not the UI itself."""

from collections import Counter

from app.repositories.models import ApplicationRecord
from app.schemas.admin import AdminMetrics, BlockedJourneySummary
from app.schemas.enums import ApplicationStepStatus
from app.services.dependency_graph import get_graph
from app.services.journey_mapper import to_domain
from app.services.sla import compute_sla_status


def compute_metrics(applications: list[ApplicationRecord]) -> AdminMetrics:
    total = len(applications)
    complete = 0
    bottlenecks: Counter[str] = Counter()
    department_pending: Counter[str] = Counter()
    department_rejected: Counter[str] = Counter()
    sla_at_risk = 0
    sla_breached = 0
    blocked_details: list[BlockedJourneySummary] = []

    for record in applications:
        journey = to_domain(record)
        if journey.is_complete():
            complete += 1

        blocked_codes = []
        for service_code, step in record.steps.items():
            if step.status == ApplicationStepStatus.BLOCKED:
                bottlenecks[service_code] += 1
                blocked_codes.append(service_code)
            department = get_graph(record.life_event_code).department_of(service_code)
            if step.status == ApplicationStepStatus.IN_PROGRESS:
                department_pending[department] += 1
            if step.status == ApplicationStepStatus.REJECTED:
                department_rejected[department] += 1
            sla_status = compute_sla_status(step.sla_due_at, step.submitted_at)
            if sla_status == "at_risk":
                sla_at_risk += 1
            elif sla_status == "breached":
                sla_breached += 1

        if blocked_codes:
            blocked_details.append(
                BlockedJourneySummary(
                    application_id=record.id,
                    citizen_id=record.citizen_id,
                    life_event_code=record.life_event_code,
                    blocked_service_codes=blocked_codes,
                )
            )

    return AdminMetrics(
        total_journeys=total,
        active_journeys=total - complete,
        complete_journeys=complete,
        blocked_journeys=len(blocked_details),
        bottleneck_service_codes=dict(bottlenecks),
        department_pending_counts=dict(department_pending),
        department_rejected_counts=dict(department_rejected),
        sla_at_risk_count=sla_at_risk,
        sla_breached_count=sla_breached,
        blocked_journey_details=blocked_details,
    )
