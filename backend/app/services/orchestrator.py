import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.schemas.enums import ApplicationStepStatus
from app.services.connectors.base import GovernmentConnector
from app.services.dependency_graph import DependencyGraph


class OrchestrationError(Exception):
    pass


class ConsentRequiredError(OrchestrationError):
    pass


class DependencyNotMetError(OrchestrationError):
    pass


@dataclass
class JourneyStep:
    service_code: str
    status: ApplicationStepStatus
    blocked_reason: str | None = None
    external_reference: str | None = None
    submitted_at: datetime | None = None
    sla_due_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Consent:
    service_code: str
    recipient_department: str
    purpose: str
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        now = datetime.now(timezone.utc)
        return self.revoked_at is None and self.expires_at > now


@dataclass
class Journey:
    id: str
    citizen_id: str
    life_event_code: str
    graph: DependencyGraph
    steps: dict[str, JourneyStep]
    consents: dict[str, Consent] = field(default_factory=dict)
    timeline: list[str] = field(default_factory=list)

    def step(self, service_code: str) -> JourneyStep:
        return self.steps[service_code]

    def is_complete(self) -> bool:
        return all(
            step.status in (ApplicationStepStatus.VERIFIED, ApplicationStepStatus.READY)
            for step in self.steps.values()
        )


class JourneyOrchestrator:
    """Owns the state-machine transitions for a citizen journey. This is
    the piece of the product that must be real — every method here
    mutates a `Journey`'s step statuses based on actual dependency
    resolution and actual connector responses, never a hardcoded UI
    animation."""

    def start_journey(
        self,
        citizen_id: str,
        life_event_code: str,
        graph: DependencyGraph,
        already_verified_service_codes: set[str],
        journey_id: str | None = None,
    ) -> Journey:
        journey = Journey(
            id=journey_id or str(uuid.uuid4()),
            citizen_id=citizen_id,
            life_event_code=life_event_code,
            graph=graph,
            steps={},
        )
        journey.timeline.append(f"Journey started for citizen {citizen_id}")
        for service_code in graph.service_codes:
            if service_code in already_verified_service_codes:
                journey.steps[service_code] = JourneyStep(
                    service_code, ApplicationStepStatus.VERIFIED
                )
            else:
                journey.steps[service_code] = JourneyStep(
                    service_code, ApplicationStepStatus.NOT_STARTED
                )
        self._recompute_dependents(journey, graph.service_codes)
        return journey

    def grant_consent(
        self, journey: Journey, service_code: str, purpose: str, validity_days: int = 30
    ) -> Consent:
        department = journey.graph.department_of(service_code)
        now = datetime.now(timezone.utc)
        consent = Consent(
            service_code=service_code,
            recipient_department=department,
            purpose=purpose,
            granted_at=now,
            expires_at=now + timedelta(days=validity_days),
        )
        journey.consents[service_code] = consent
        journey.timeline.append(
            f"Consent granted to share data with {department} for {service_code}"
        )
        return consent

    def revoke_consent(self, journey: Journey, service_code: str) -> None:
        consent = journey.consents.get(service_code)
        if consent:
            consent.revoked_at = datetime.now(timezone.utc)
            journey.timeline.append(f"Consent revoked for {service_code}")

    def submit_to_connector(
        self,
        journey: Journey,
        service_code: str,
        connector: GovernmentConnector,
        payload: dict,
    ) -> str:
        step = journey.step(service_code)
        if step.status not in (ApplicationStepStatus.NOT_STARTED, ApplicationStepStatus.BLOCKED):
            raise OrchestrationError(
                f"{service_code} is not in a submittable state (currently {step.status})"
            )
        unmet = [
            req
            for req in journey.graph.requirements_of(service_code)
            if journey.step(req).status != ApplicationStepStatus.VERIFIED
        ]
        if unmet:
            raise DependencyNotMetError(
                f"{service_code} cannot be submitted before {', '.join(unmet)} {'is' if len(unmet) == 1 else 'are'} verified"
            )
        consent = journey.consents.get(service_code)
        if not consent or not consent.is_active:
            raise ConsentRequiredError(f"Active consent required before submitting {service_code}")

        response = connector.submit(service_code, payload)
        step.status = ApplicationStepStatus.IN_PROGRESS
        step.external_reference = response.external_reference
        step.submitted_at = response.timestamp
        step.sla_due_at = response.sla_deadline
        step.updated_at = datetime.now(timezone.utc)
        journey.timeline.append(
            f"{service_code} submitted to {connector.department} — "
            f"reference {response.external_reference}"
        )
        return response.external_reference

    def receive_connector_event(
        self, journey: Journey, service_code: str, event_status: str
    ) -> list[str]:
        """Applies a webhook/n8n event to a step and cascades the effect
        to any dependent steps. Returns the list of service_codes whose
        status changed as a result (for asserting the 'automatic unlock'
        behavior)."""
        step = journey.step(service_code)
        changed = []

        if event_status == "approved":
            step.status = ApplicationStepStatus.VERIFIED
            journey.timeline.append(f"{service_code} VERIFIED (department approval received)")
            changed.append(service_code)
        elif event_status == "rejected":
            step.status = ApplicationStepStatus.REJECTED
            journey.timeline.append(f"{service_code} REJECTED by department")
            changed.append(service_code)
        else:
            raise OrchestrationError(f"Unknown event_status: {event_status}")

        step.updated_at = datetime.now(timezone.utc)
        changed.extend(self._recompute_dependents(journey, journey.graph.dependents_of(service_code)))
        return changed

    def _recompute_dependents(self, journey: Journey, service_codes: list[str]) -> list[str]:
        changed = []
        for service_code in service_codes:
            step = journey.steps[service_code]
            if step.status in (ApplicationStepStatus.VERIFIED, ApplicationStepStatus.IN_PROGRESS):
                continue
            requirements = journey.graph.requirements_of(service_code)
            if not requirements:
                continue
            rejected = [r for r in requirements if journey.steps[r].status == ApplicationStepStatus.REJECTED]
            unmet = [r for r in requirements if journey.steps[r].status != ApplicationStepStatus.VERIFIED]
            before = step.status
            if rejected:
                step.status = ApplicationStepStatus.BLOCKED
                names = ", ".join(journey.graph.display_name_of(r) for r in rejected)
                step.blocked_reason = f"{names} was rejected"
            elif not unmet:
                step.status = ApplicationStepStatus.READY
                step.blocked_reason = None
            else:
                step.status = ApplicationStepStatus.BLOCKED
                names = ", ".join(journey.graph.display_name_of(r) for r in unmet)
                step.blocked_reason = f"Waiting for {names}"
            if step.status != before:
                step.updated_at = datetime.now(timezone.utc)
                journey.timeline.append(
                    f"{service_code} -> {step.status.value} ({step.blocked_reason or 'all requirements satisfied'})"
                )
                changed.append(service_code)
        return changed
