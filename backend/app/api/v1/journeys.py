import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.core.container import (
    get_application_repository,
    get_connector_for_department,
    get_document_repository,
    get_journey_service,
)
from app.core.security import get_current_session, require_owner_or_admin
from app.repositories.models import SessionRecord
from app.schemas.journey import (
    GrantConsentRequest,
    JourneyConsentView,
    JourneyDetailView,
    JourneyStepView,
    JourneySummaryView,
    StartJourneyRequest,
    SubmitRequest,
)
from app.services import journey_narrative, vault_eligibility
from app.services.dependency_graph import get_graph
from app.services.life_event_catalog import get_life_event_meta
from app.services.orchestrator import Journey, OrchestrationError
from app.services.sla import compute_sla_status

router = APIRouter(tags=["journeys"])


def _to_detail(journey: Journey) -> JourneyDetailView:
    meta = get_life_event_meta(journey.life_event_code)
    steps = []
    for code, step in journey.steps.items():
        consent = journey.consents.get(code)
        steps.append(
            JourneyStepView(
                service_code=code,
                display_name=journey.graph.display_name_of(code),
                department=journey.graph.department_of(code),
                status=step.status,
                blocked_reason=step.blocked_reason,
                requires_service_codes=journey.graph.requirements_of(code),
                external_reference=step.external_reference,
                submitted_at=step.submitted_at,
                sla_due_at=step.sla_due_at,
                sla_status=compute_sla_status(step.sla_due_at, step.submitted_at),
                consent=JourneyConsentView(
                    service_code=consent.service_code,
                    recipient_department=consent.recipient_department,
                    purpose=consent.purpose,
                    granted_at=consent.granted_at,
                    expires_at=consent.expires_at,
                    revoked_at=consent.revoked_at,
                    is_active=consent.is_active,
                )
                if consent
                else None,
            )
        )
    return JourneyDetailView(
        application_id=journey.id,
        citizen_id=journey.citizen_id,
        life_event_code=journey.life_event_code,
        life_event_title_en=meta.title_en,
        life_event_title_mr=meta.title_mr,
        goal_statement_en=meta.goal_statement_en,
        steps=steps,
        timeline=journey.timeline,
        is_complete=journey.is_complete(),
        current_blocker=journey_narrative.current_blocker(journey),
        next_action=journey_narrative.next_action(journey),
    )


@router.post("/citizens/{citizen_id}/journeys", response_model=JourneyDetailView, status_code=201)
def start_journey(
    citizen_id: str,
    request: StartJourneyRequest,
    session: SessionRecord = Depends(get_current_session),
) -> JourneyDetailView:
    require_owner_or_admin(citizen_id, session)
    try:
        graph = get_graph(request.life_event_code)
        get_life_event_meta(request.life_event_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    verified = vault_eligibility.verified_service_codes_from_vault(
        citizen_id, get_document_repository()
    )
    journey = get_journey_service().start_or_reset_journey(
        application_id=str(uuid.uuid4()),
        citizen_id=citizen_id,
        life_event_code=request.life_event_code,
        graph=graph,
        already_verified_service_codes=verified,
    )
    return _to_detail(journey)


@router.get("/citizens/{citizen_id}/journeys", response_model=list[JourneySummaryView])
def list_journeys(
    citizen_id: str, session: SessionRecord = Depends(get_current_session)
) -> list[JourneySummaryView]:
    require_owner_or_admin(citizen_id, session)
    records = get_application_repository().list_for_citizen(citizen_id)
    summaries = []
    for record in records:
        journey = get_journey_service().get_journey(record.id)
        assert journey is not None
        meta = get_life_event_meta(record.life_event_code)
        summaries.append(
            JourneySummaryView(
                application_id=record.id,
                citizen_id=record.citizen_id,
                life_event_code=record.life_event_code,
                life_event_title_en=meta.title_en,
                is_complete=journey.is_complete(),
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )
    return sorted(summaries, key=lambda s: s.updated_at, reverse=True)


def _require_owned_journey(application_id: str, session: SessionRecord) -> Journey:
    journey = get_journey_service().get_journey(application_id)
    if journey is None:
        raise HTTPException(status_code=404, detail=f"No journey found with id {application_id}")
    require_owner_or_admin(journey.citizen_id, session)
    return journey


@router.get("/journeys/{application_id}", response_model=JourneyDetailView)
def get_journey_detail(
    application_id: str, session: SessionRecord = Depends(get_current_session)
) -> JourneyDetailView:
    return _to_detail(_require_owned_journey(application_id, session))


@router.post("/journeys/{application_id}/consent/{service_code}", response_model=JourneyDetailView)
def grant_consent(
    application_id: str,
    service_code: str,
    request: GrantConsentRequest,
    session: SessionRecord = Depends(get_current_session),
) -> JourneyDetailView:
    _require_owned_journey(application_id, session)
    try:
        journey = get_journey_service().grant_consent(application_id, service_code, request.purpose)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_detail(journey)


@router.post(
    "/journeys/{application_id}/consent/{service_code}/revoke", response_model=JourneyDetailView
)
def revoke_consent(
    application_id: str,
    service_code: str,
    session: SessionRecord = Depends(get_current_session),
) -> JourneyDetailView:
    _require_owned_journey(application_id, session)
    journey = get_journey_service().revoke_consent(application_id, service_code)
    return _to_detail(journey)


@router.post("/journeys/{application_id}/submit/{service_code}", response_model=JourneyDetailView)
def submit_service(
    application_id: str,
    service_code: str,
    request: SubmitRequest,
    session: SessionRecord = Depends(get_current_session),
) -> JourneyDetailView:
    journey = _require_owned_journey(application_id, session)
    try:
        department = journey.graph.department_of(service_code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown service_code {service_code!r}") from exc
    try:
        connector = get_connector_for_department(department)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    try:
        journey = get_journey_service().submit_to_connector(
            application_id, service_code, connector, payload=request.payload
        )
    except OrchestrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_detail(journey)


@router.post("/journeys/{application_id}/approve/{service_code}", response_model=JourneyDetailView)
def approve_service(
    application_id: str,
    service_code: str,
    session: SessionRecord = Depends(get_current_session),
) -> JourneyDetailView:
    """Generic version of the /demo approve action: simulates the
    department system approving whatever was last submitted for this
    service, then runs it through the same receive_connector_event every
    other event source uses."""
    journey = _require_owned_journey(application_id, session)
    step = journey.step(service_code)
    if step.external_reference is None:
        raise HTTPException(status_code=409, detail=f"{service_code} has not been submitted yet")
    department = journey.graph.department_of(service_code)
    connector = get_connector_for_department(department)
    connector.simulate_approval(step.external_reference)
    try:
        journey = get_journey_service().receive_connector_event(
            application_id, service_code, event_status="approved"
        )
    except OrchestrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_detail(journey)
