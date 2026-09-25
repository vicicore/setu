from datetime import datetime

from pydantic import BaseModel

from app.schemas.enums import ApplicationStepStatus, SlaStatus


class DemoCatalogService(BaseModel):
    service_code: str
    display_name: str
    department: str
    requires_service_codes: list[str]


class DemoCatalogView(BaseModel):
    citizen_id: str
    life_event_code: str
    citizen_goal_statement_en: str
    citizen_goal_statement_mr: str
    services: list[DemoCatalogService]


class DemoStepView(BaseModel):
    service_code: str
    display_name: str
    department: str
    status: ApplicationStepStatus
    blocked_reason: str | None
    external_reference: str | None
    submitted_at: datetime | None
    sla_due_at: datetime | None
    sla_status: SlaStatus | None


class DemoJourneyView(BaseModel):
    application_id: str
    citizen_id: str
    steps: list[DemoStepView]
    timeline: list[str]
    is_complete: bool


class DemoAuditEntryView(BaseModel):
    id: str
    actor: str
    action: str
    metadata: dict
    created_at: datetime
