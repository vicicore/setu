from uuid import UUID

from pydantic import BaseModel

from app.schemas.enums import ApplicationStepStatus


class EligibilityEvaluateRequest(BaseModel):
    citizen_id: UUID
    life_event_id: UUID


class ServiceEligibility(BaseModel):
    service_code: str
    service_name: str
    status: ApplicationStepStatus
    reasons: list[str] = []
    missing_attributes: list[str] = []
    missing_documents: list[str] = []


class EligibilityEvaluateResult(BaseModel):
    life_event_id: UUID
    citizen_id: UUID
    services: list[ServiceEligibility]
    overall_ready: bool
