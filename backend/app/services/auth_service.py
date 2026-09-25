"""Real, server-side authentication — deliberately not Aadhaar-backed.

An `identifier` is a demo-safe stand-in a citizen logs in with (a phone
number in a real deployment; any non-empty string here). The server
issues an opaque bearer token and is the only party that can resolve it
back to a citizen_id — the frontend can no longer just type a citizen_id
into a field and have the backend believe it (Phase 7 priority 2/3).

This is architected as the seam Supabase Auth slots into later: replace
`AuthService`'s token issuance/verification with Supabase JWT
verification, keep `get_current_session`'s call signature the same, and
every endpoint below it needs zero changes."""

import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.repositories.interfaces import AuthRepository
from app.repositories.models import AccountRecord, SessionRecord
from app.services.identity import derive_citizen_id


class AuthService:
    def __init__(self, auth_repo: AuthRepository) -> None:
        self._auth = auth_repo

    def login_or_register(self, identifier: str) -> SessionRecord:
        identifier = identifier.strip()
        if not identifier:
            raise ValueError("identifier must not be empty")

        account = self._auth.get_account_by_identifier(identifier)
        if account is None:
            settings = get_settings()
            role = "admin" if identifier in settings.admin_identifiers else "citizen"
            citizen_id = derive_citizen_id(identifier)
            account = AccountRecord(
                citizen_id=citizen_id,
                identifier=identifier,
                role=role,
                created_at=datetime.now(timezone.utc),
            )
            self._auth.create_account(account)

        settings = get_settings()
        now = datetime.now(timezone.utc)
        session = SessionRecord(
            token=secrets.token_urlsafe(32),
            citizen_id=account.citizen_id,
            role=account.role,
            created_at=now,
            expires_at=now + timedelta(hours=settings.session_ttl_hours),
        )
        self._auth.create_session(session)
        return session

    def resolve_session(self, token: str) -> SessionRecord | None:
        session = self._auth.get_session(token)
        if session is None:
            return None
        if session.expires_at <= datetime.now(timezone.utc):
            return None
        return session

    def logout(self, token: str) -> None:
        self._auth.delete_session(token)
