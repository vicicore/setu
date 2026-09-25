"""FastAPI dependencies enforcing authentication/authorization. Every
citizen-facing endpoint that takes a citizen_id path parameter must
depend on `require_owner_or_admin` (or `get_current_session` directly)
— never trust the path parameter alone. See docs/DECISIONS.md for why
this shape survives swapping in real Supabase JWT verification later."""

from fastapi import Header, HTTPException

from app.core.container import get_auth_service
from app.repositories.models import SessionRecord


def get_current_session(authorization: str | None = Header(default=None)) -> SessionRecord:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    session = get_auth_service().resolve_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session


def require_owner_or_admin(citizen_id: str, session: SessionRecord) -> None:
    """Call at the top of any handler with a citizen_id path parameter.
    Raises 403 unless the authenticated session belongs to that citizen
    or holds the admin role — this is what stops Citizen A from reading
    Citizen B's data by editing a URL."""
    if session.citizen_id != citizen_id and session.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized for this citizen")


def require_admin(session: SessionRecord) -> None:
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
