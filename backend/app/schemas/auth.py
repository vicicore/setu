from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    identifier: str


class SessionView(BaseModel):
    token: str
    citizen_id: str
    role: str
    expires_at: datetime


class MeView(BaseModel):
    citizen_id: str
    role: str
