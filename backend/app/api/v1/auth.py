from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.container import get_auth_service
from app.core.security import get_current_session
from app.repositories.models import SessionRecord
from app.schemas.auth import LoginRequest, MeView, SessionView

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/session", response_model=SessionView)
def login_or_register(request: LoginRequest) -> SessionView:
    """Not Aadhaar. A demo-safe identifier (a phone number in a real
    deployment) that the server turns into an opaque bearer token — the
    frontend can no longer just assert a citizen_id and be believed."""
    try:
        session = get_auth_service().login_or_register(request.identifier)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SessionView(
        token=session.token,
        citizen_id=session.citizen_id,
        role=session.role,
        expires_at=session.expires_at,
    )


@router.get("/me", response_model=MeView)
def get_me(session: SessionRecord = Depends(get_current_session)) -> MeView:
    return MeView(citizen_id=session.citizen_id, role=session.role)


@router.post("/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)) -> None:
    if authorization and authorization.startswith("Bearer "):
        get_auth_service().logout(authorization.removeprefix("Bearer ").strip())
