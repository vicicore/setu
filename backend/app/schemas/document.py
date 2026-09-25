from datetime import datetime

from pydantic import BaseModel

from app.schemas.enums import DocumentStatus


class DocumentUsedByJourney(BaseModel):
    application_id: str
    life_event_title_en: str
    service_code: str


class DocumentView(BaseModel):
    id: str
    citizen_id: str
    doc_type: str
    issuer: str | None
    original_filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    rejection_reason: str | None
    url: str
    created_at: datetime
    updated_at: datetime
    used_by: list[DocumentUsedByJourney] = []


class DocumentRejectRequest(BaseModel):
    reason: str
