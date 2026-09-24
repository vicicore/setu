from uuid import UUID

from pydantic import BaseModel


class Service(BaseModel):
    id: UUID
    code: str
    name: str
    department: str
    sla_days: int
    description: str | None = None


class ServiceDependency(BaseModel):
    service: Service
    depends_on: Service | None = None
    sequence_order: int


class LifeEvent(BaseModel):
    id: UUID
    code: str
    title_en: str
    title_mr: str | None = None
    title_hi: str | None = None
    description: str | None = None


class LifeEventDetail(LifeEvent):
    dependency_graph: list[ServiceDependency]


class LifeEventResolveRequest(BaseModel):
    statement: str
    language: str = "en"


class LifeEventResolveResult(BaseModel):
    matched_life_event: LifeEvent | None
    confidence: float
    candidates: list[LifeEvent] = []
