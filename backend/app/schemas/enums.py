from enum import StrEnum


class DocumentStatus(StrEnum):
    """A document's real verification lifecycle. Uploading a file is not
    the same as it being verified — only VERIFIED documents count toward
    eligibility (see app/services/vault_eligibility.py)."""

    UPLOADED = "uploaded"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApplicationStepStatus(StrEnum):
    NOT_STARTED = "not_started"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    READY = "ready"
    REJECTED = "rejected"


class SlaStatus(StrEnum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BREACHED = "breached"


class ConsentStatus(StrEnum):
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class OfficialRole(StrEnum):
    DEPARTMENT_OFFICER = "department_officer"
    DISTRICT_ADMIN = "district_admin"
    SUPER_ADMIN = "super_admin"
