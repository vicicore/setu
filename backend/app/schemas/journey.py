from datetime import datetime

from pydantic import BaseModel

from app.schemas.enums import ApplicationStepStatus, SlaStatus


class JourneyConsentView(BaseModel):
    service_code: str
    recipient_department: str
    purpose: str
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    is_active: bool


class JourneyStepView(BaseModel):
    service_code: str
    display_name: str
    department: str
    status: ApplicationStepStatus
    blocked_reason: str | None
    requires_service_codes: list[str]
    external_reference: str | None
    submitted_at: datetime | None
    sla_due_at: datetime | None
    sla_status: SlaStatus | None
    consent: JourneyConsentView | None


class JourneySummaryView(BaseModel):
    application_id: str
    citizen_id: str
    life_event_code: str
    life_event_title_en: str
    is_complete: bool
    created_at: datetime
    updated_at: datetime


class JourneyDetailView(BaseModel):
    application_id: str
    citizen_id: str
    life_event_code: str
    life_event_title_en: str
    life_event_title_mr: str
    goal_statement_en: str
    steps: list[JourneyStepView]
    timeline: list[str]
    is_complete: bool
    current_blocker: str | None
    next_action: str


class StartJourneyRequest(BaseModel):
    life_event_code: str


class GrantConsentRequest(BaseModel):
    purpose: str


class SubmitRequest(BaseModel):
    payload: dict = {}
