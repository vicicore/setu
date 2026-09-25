from pydantic import BaseModel


class BlockedJourneySummary(BaseModel):
    application_id: str
    citizen_id: str
    life_event_code: str
    blocked_service_codes: list[str]


class AdminMetrics(BaseModel):
    total_journeys: int
    active_journeys: int
    complete_journeys: int
    blocked_journeys: int
    bottleneck_service_codes: dict[str, int]
    department_pending_counts: dict[str, int]
    department_rejected_counts: dict[str, int]
    sla_at_risk_count: int
    sla_breached_count: int
    blocked_journey_details: list[BlockedJourneySummary]
