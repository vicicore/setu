from datetime import datetime

from pydantic import BaseModel

from app.schemas.enums import DocumentStatus


class DocumentView(BaseModel):
    id: str
    citizen_id: str
    doc_type: str
    issuer: str | None
    original_filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    url: str
    created_at: datetime
