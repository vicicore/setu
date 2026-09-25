from pydantic import BaseModel


class LifeEventService(BaseModel):
    service_code: str
    display_name: str
    department: str
    requires_service_codes: list[str]


class LifeEventSummary(BaseModel):
    code: str
    title_en: str
    title_mr: str
    description_en: str
    description_mr: str


class LifeEventDetail(LifeEventSummary):
    goal_statement_en: str
    goal_statement_mr: str
    services: list[LifeEventService]
