"""One function, used by both the auth system and the demo seeding, so
a citizen_id is always derived the same way from a login identifier —
never two competing definitions of "who is this citizen"."""

import hashlib


def derive_citizen_id(identifier: str) -> str:
    return f"citizen-{hashlib.sha256(identifier.encode()).hexdigest()[:16]}"
