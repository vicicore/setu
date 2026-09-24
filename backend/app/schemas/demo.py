from pydantic import BaseModel

from app.schemas.enums import ApplicationStepStatus


class DemoStepView(BaseModel):
    service_code: str
    display_name: str
    department: str
    status: ApplicationStepStatus
    blocked_reason: str | None
    external_reference: str | None


class DemoJourneyView(BaseModel):
    citizen_id: str
    steps: list[DemoStepView]
    timeline: list[str]
    is_complete: bool
