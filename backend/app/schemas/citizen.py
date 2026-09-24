from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CitizenProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    dob: date | None = None
    district: str | None = None
    taluka: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred_language: str = "en"
    created_at: datetime
    updated_at: datetime


class CitizenProfileUpdate(BaseModel):
    full_name: str | None = None
    dob: date | None = None
    district: str | None = None
    taluka: str | None = None
    phone: str | None = None
    preferred_language: str | None = None


class ProfileCompleteness(BaseModel):
    citizen_id: UUID
    profile_completeness_pct: int
    verified_attributes: dict
    linked_identifiers_redacted: dict
