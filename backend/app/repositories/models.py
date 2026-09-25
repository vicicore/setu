"""Serializable persistence records for the journey aggregate. Kept
distinct from the in-memory domain objects in app/services/orchestrator.py
— those carry a live DependencyGraph reference and are not meant to be
serialized directly. app/services/journey_mapper.py converts between the
two. This separation is what lets a JSON-file adapter and a future
Supabase adapter both produce/consume the same domain Journey."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.enums import ApplicationStepStatus


class StepRecord(BaseModel):
    service_code: str
    status: ApplicationStepStatus
    blocked_reason: str | None = None
    external_reference: str | None = None
    submitted_at: datetime | None = None
    sla_due_at: datetime | None = None
    updated_at: datetime


class ConsentRecord(BaseModel):
    service_code: str
    recipient_department: str
    purpose: str
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class ApplicationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    citizen_id: str
    life_event_code: str
    steps: dict[str, StepRecord]
    consents: dict[str, ConsentRecord] = Field(default_factory=dict)
    timeline: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AuditLogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    application_id: str | None = None
    actor: str
    action: str
    resource_type: str
    resource_id: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
