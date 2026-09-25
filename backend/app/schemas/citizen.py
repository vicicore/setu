from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CitizenProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    citizen_id: str
    full_name: str
    dob: str | None = None
    district: str | None = None
    taluka: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred_language: str = "en"
    profile_completeness_pct: int
    created_at: datetime
    updated_at: datetime


class CitizenProfileUpdate(BaseModel):
    full_name: str | None = None
    dob: date | None = None
    district: str | None = None
    taluka: str | None = None
    phone: str | None = None
    preferred_language: str | None = None
