from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.container import (
    get_document_repository,
    get_document_vault_service,
    get_journey_service,
    get_revenue_connector,
)
from app.schemas.demo import (
    DemoAuditEntryView,
    DemoCatalogService,
    DemoCatalogView,
    DemoJourneyView,
    DemoStepView,
)
from app.services import demo_scenario, vault_eligibility
from app.services.document_service import DocumentNotFoundError, InvalidDocumentTransitionError
from app.services.orchestrator import Journey, OrchestrationError
from app.services.sla import compute_sla_status
from app.services.vault_integration import verify_document_and_sync_journeys

router = APIRouter(prefix="/demo", tags=["demo"])


def _require_demo_mode() -> None:
    if not get_settings().demo_mode_enabled:
        raise HTTPException(status_code=404, detail="Demo mode is disabled")


def _journey_view(journey: Journey) -> DemoJourneyView:
    steps = []
    for code, step in journey.steps.items():
        steps.append(
            DemoStepView(
                service_code=code,
                display_name=journey.graph.display_name_of(code),
                department=journey.graph.department_of(code),
                status=step.status,
                blocked_reason=step.blocked_reason,
                external_reference=step.external_reference,
                submitted_at=step.submitted_at,
                sla_due_at=step.sla_due_at,
                sla_status=compute_sla_status(step.sla_due_at, step.submitted_at),
            )
        )
    return DemoJourneyView(
        application_id=journey.id,
        citizen_id=journey.citizen_id,
        steps=steps,
        timeline=journey.timeline,
        is_complete=journey.is_complete(),
    )


def _reset_vault_and_journey() -> Journey:
    """The one place that seeds the vault and starts/resets the journey
    from it — used by both POST /demo/reset and the auto-start fallback
    in GET /demo/journey, so there is exactly one seeding path."""
    vault = get_document_vault_service()
    demo_scenario.reset_demo_vault(vault)
    verified = vault_eligibility.verified_service_codes_from_vault(
        demo_scenario.DEMO_CITIZEN_ID, get_document_repository()
    )
    return get_journey_service().start_or_reset_journey(
        application_id=demo_scenario.DEMO_APPLICATION_ID,
        citizen_id=demo_scenario.DEMO_CITIZEN_ID,
        life_event_code=demo_scenario.DEMO_LIFE_EVENT_CODE,
        graph=demo_scenario.DEMO_GRAPH,
        already_verified_service_codes=verified,
    )


def _find_pending_caste_document_id() -> str:
    documents = get_document_repository().list_for_citizen(demo_scenario.DEMO_CITIZEN_ID)
    for doc in documents:
        if doc.doc_type == demo_scenario.SEED_PENDING_DOC_TYPE:
            return doc.id
    raise HTTPException(
        status_code=404,
        detail="No caste certificate document found — reset the demo first",
    )


@router.get("/catalog", response_model=DemoCatalogView)
def get_catalog() -> DemoCatalogView:
    _require_demo_mode()
    return DemoCatalogView(
        citizen_id=demo_scenario.DEMO_CITIZEN_ID,
        login_identifier=demo_scenario.DEMO_LOGIN_IDENTIFIER,
        life_event_code=demo_scenario.DEMO_LIFE_EVENT_CODE,
        citizen_goal_statement_en=demo_scenario.CITIZEN_GOAL_STATEMENT_EN,
        citizen_goal_statement_mr=demo_scenario.CITIZEN_GOAL_STATEMENT_MR,
        services=[
            DemoCatalogService(
                service_code=s.service_code,
                display_name=s.display_name,
                department=s.department,
                requires_service_codes=s.requires_service_codes,
            )
            for s in demo_scenario.catalog()
        ],
    )


@router.get("/journey", response_model=DemoJourneyView)
def get_journey() -> DemoJourneyView:
    _require_demo_mode()
    journey = get_journey_service().get_journey(demo_scenario.DEMO_APPLICATION_ID)
    if journey is None:
        journey = _reset_vault_and_journey()
    return _journey_view(journey)


@router.post("/reset", response_model=DemoJourneyView)
def reset_demo() -> DemoJourneyView:
    _require_demo_mode()
    return _journey_view(_reset_vault_and_journey())


@router.post("/consent/income-certificate", response_model=DemoJourneyView)
def grant_income_consent() -> DemoJourneyView:
    _require_demo_mode()
    try:
        journey = get_journey_service().grant_consent(
            demo_scenario.DEMO_APPLICATION_ID,
            "income_certificate",
            purpose="Verify family income for engineering scholarship eligibility",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _journey_view(journey)


@router.post("/actions/submit-income-certificate", response_model=DemoJourneyView)
def submit_income_certificate() -> DemoJourneyView:
    _require_demo_mode()
    try:
        journey = get_journey_service().submit_to_connector(
            demo_scenario.DEMO_APPLICATION_ID,
            "income_certificate",
            get_revenue_connector(),
            payload={"citizen_id": demo_scenario.DEMO_CITIZEN_ID, "declared_income_inr": 185000},
        )
    except OrchestrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _journey_view(journey)


@router.post("/actions/approve-income-certificate", response_model=DemoJourneyView)
def approve_income_certificate() -> DemoJourneyView:
    _require_demo_mode()
    service = get_journey_service()
    journey = service.get_journey(demo_scenario.DEMO_APPLICATION_ID)
    if journey is None:
        raise HTTPException(status_code=404, detail="Demo journey not started yet")
    step = journey.step("income_certificate")
    if step.external_reference is None:
        raise HTTPException(
            status_code=409, detail="Income certificate has not been submitted yet"
        )
    get_revenue_connector().simulate_approval(step.external_reference)
    try:
        journey = service.receive_connector_event(
            demo_scenario.DEMO_APPLICATION_ID, "income_certificate", event_status="approved"
        )
    except OrchestrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _journey_view(journey)


@router.post("/actions/submit-caste-certificate-for-review", response_model=DemoJourneyView)
def submit_caste_certificate_for_review() -> DemoJourneyView:
    """Demonstrates the document lifecycle's first real transition
    (UPLOADED -> UNDER_REVIEW) on a document that is genuinely sitting
    in the vault unreviewed — separate from, and without touching, the
    connector-based income certificate flow."""
    _require_demo_mode()
    document_id = _find_pending_caste_document_id()
    try:
        get_document_vault_service().submit_for_review(document_id)
    except (DocumentNotFoundError, InvalidDocumentTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    journey = get_journey_service().get_journey(demo_scenario.DEMO_APPLICATION_ID)
    assert journey is not None
    return _journey_view(journey)


@router.post("/actions/verify-caste-certificate", response_model=DemoJourneyView)
def verify_caste_certificate() -> DemoJourneyView:
    """The vault -> journey cascade, live: verifying this document calls
    the exact same JourneyService.receive_connector_event the Revenue
    webhook uses (via sync_verified_document) — a second, independent
    channel into the one orchestration state machine, not a parallel one."""
    _require_demo_mode()
    document_id = _find_pending_caste_document_id()
    vault = get_document_vault_service()
    journeys = get_journey_service()
    try:
        verify_document_and_sync_journeys(document_id, vault, journeys)
    except (DocumentNotFoundError, InvalidDocumentTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    journey = journeys.get_journey(demo_scenario.DEMO_APPLICATION_ID)
    assert journey is not None
    return _journey_view(journey)


@router.get("/sla-alerts", response_model=list[DemoStepView])
def get_sla_alerts() -> list[DemoStepView]:
    """Polled by the sla-monitoring n8n workflow (infra/n8n/workflows/) —
    returns only steps whose SLA is at_risk or breached, computed live
    from the same `compute_sla_status` the journey view uses."""
    _require_demo_mode()
    journey = get_journey_service().get_journey(demo_scenario.DEMO_APPLICATION_ID)
    if journey is None:
        return []
    view = _journey_view(journey)
    return [s for s in view.steps if s.sla_status in ("at_risk", "breached")]


@router.get("/audit-log", response_model=list[DemoAuditEntryView])
def get_audit_log() -> list[DemoAuditEntryView]:
    _require_demo_mode()
    entries = get_journey_service().audit_trail(demo_scenario.DEMO_APPLICATION_ID)
    return [
        DemoAuditEntryView(
            id=e.id, actor=e.actor, action=e.action, metadata=e.metadata, created_at=e.created_at
        )
        for e in entries
    ]
