from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas.demo import DemoJourneyView, DemoStepView
from app.services.demo_store import get_demo_session
from app.services.orchestrator import OrchestrationError

router = APIRouter(prefix="/demo", tags=["demo"])


def _require_demo_mode() -> None:
    if not get_settings().demo_mode_enabled:
        raise HTTPException(status_code=404, detail="Demo mode is disabled")


def _journey_view() -> DemoJourneyView:
    session = get_demo_session()
    journey = session.journey
    steps = [
        DemoStepView(
            service_code=code,
            display_name=journey.graph.display_name_of(code),
            department=journey.graph.department_of(code),
            status=step.status,
            blocked_reason=step.blocked_reason,
            external_reference=step.external_reference,
        )
        for code, step in journey.steps.items()
    ]
    return DemoJourneyView(
        citizen_id=journey.citizen_id,
        steps=steps,
        timeline=journey.timeline,
        is_complete=journey.is_complete(),
    )


@router.get("/journey", response_model=DemoJourneyView)
def get_journey() -> DemoJourneyView:
    _require_demo_mode()
    return _journey_view()


@router.post("/reset", response_model=DemoJourneyView)
def reset_demo() -> DemoJourneyView:
    _require_demo_mode()
    get_demo_session().reset()
    return _journey_view()


@router.post("/consent/income-certificate", response_model=DemoJourneyView)
def grant_income_consent() -> DemoJourneyView:
    _require_demo_mode()
    get_demo_session().grant_consent()
    return _journey_view()


@router.post("/actions/submit-income-certificate", response_model=DemoJourneyView)
def submit_income_certificate() -> DemoJourneyView:
    _require_demo_mode()
    try:
        get_demo_session().submit_income_certificate()
    except OrchestrationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _journey_view()


@router.post("/actions/approve-income-certificate", response_model=DemoJourneyView)
def approve_income_certificate() -> DemoJourneyView:
    _require_demo_mode()
    try:
        get_demo_session().approve_income_certificate()
    except (OrchestrationError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _journey_view()
