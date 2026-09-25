from fastapi import APIRouter, HTTPException

from app.schemas.eligibility import EligibilityEvaluateRequest, EligibilityEvaluateResult
from app.services import eligibility as eligibility_engine
from app.services.dependency_graph import get_graph

router = APIRouter(prefix="/eligibility", tags=["eligibility"])


@router.post("/evaluate", response_model=EligibilityEvaluateResult)
def evaluate_eligibility(request: EligibilityEvaluateRequest) -> EligibilityEvaluateResult:
    try:
        graph = get_graph(request.life_event_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return eligibility_engine.evaluate(
        life_event_code=request.life_event_code,
        graph=graph,
        verified_service_codes=set(request.verified_service_codes),
    )
