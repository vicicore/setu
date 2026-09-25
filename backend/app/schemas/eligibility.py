from pydantic import BaseModel

from app.schemas.enums import ApplicationStepStatus


class ServiceEligibility(BaseModel):
    service_code: str
    display_name: str
    department: str
    status: ApplicationStepStatus
    requires_service_codes: list[str]
    reasons: list[str] = []


class EligibilityEvaluateResult(BaseModel):
    life_event_code: str
    services: list[ServiceEligibility]
    overall_ready: bool


class EligibilityEvaluateRequest(BaseModel):
    """Used only by the low-level /eligibility/evaluate-raw endpoint for
    testing the rule engine against an arbitrary hypothetical state. The
    normal citizen-facing flow is GET /citizens/{citizen_id}/eligibility/
    {life_event_code}, which computes verified_service_codes from the
    citizen's actual verified vault documents — see
    app/services/vault_eligibility.py. Do not wire this request shape
    into any citizen-facing UI."""

    life_event_code: str
    verified_service_codes: list[str] = []
