from fastapi import APIRouter, Depends, HTTPException

from app.core.container import get_application_repository, get_document_repository
from app.core.security import get_current_session, require_owner_or_admin
from app.repositories.models import SessionRecord
from app.schemas.eligibility import EligibilityEvaluateRequest, EligibilityEvaluateResult
from app.services import eligibility as eligibility_engine
from app.services import vault_eligibility
from app.services.dependency_graph import get_graph

router = APIRouter(tags=["eligibility"])


@router.get(
    "/citizens/{citizen_id}/eligibility/{life_event_code}",
    response_model=EligibilityEvaluateResult,
)
def evaluate_citizen_eligibility(
    citizen_id: str,
    life_event_code: str,
    session: SessionRecord = Depends(get_current_session),
) -> EligibilityEvaluateResult:
    """The normal flow: verified_service_codes is computed from the
    citizen's actual verified vault documents plus any already-verified
    step in one of their applications (so a requirement satisfied via a
    government connector, not just the vault, is reflected here too —
    otherwise this view would go stale the moment a connector approval
    landed). Never supplied by the caller. This is what /demo and any
    citizen-facing UI should call."""
    require_owner_or_admin(citizen_id, session)
    try:
        graph = get_graph(life_event_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    verified = vault_eligibility.verified_service_codes_for_citizen(
        citizen_id, get_document_repository(), get_application_repository()
    )
    return eligibility_engine.evaluate(
        life_event_code=life_event_code, graph=graph, verified_service_codes=verified
    )


@router.post("/eligibility/evaluate-raw", response_model=EligibilityEvaluateResult)
def evaluate_eligibility_raw(request: EligibilityEvaluateRequest) -> EligibilityEvaluateResult:
    """Low-level access to the rule engine for testing an arbitrary
    hypothetical verified set. Not for citizen-facing use — see the
    docstring on EligibilityEvaluateRequest."""
    try:
        graph = get_graph(request.life_event_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return eligibility_engine.evaluate(
        life_event_code=request.life_event_code,
        graph=graph,
        verified_service_codes=set(request.verified_service_codes),
    )
