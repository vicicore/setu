from pydantic import BaseModel

from app.schemas.enums import ApplicationStepStatus


class EligibilityEvaluateRequest(BaseModel):
    """Deliberately takes life_event_code + an explicit list of already-
    verified service codes, rather than a citizen_id looked up against a
    live Supabase profile — there is no persisted citizen/document vault
    wired to eligibility yet (that's later work; see docs/DECISIONS.md).
    This keeps the rule engine itself real and testable without faking a
    profile store underneath it."""

    life_event_code: str
    verified_service_codes: list[str] = []


class ServiceEligibility(BaseModel):
    service_code: str
    display_name: str
    department: str
    status: ApplicationStepStatus
    depends_on_service_code: str | None
    reasons: list[str] = []


class EligibilityEvaluateResult(BaseModel):
    life_event_code: str
    services: list[ServiceEligibility]
    overall_ready: bool
