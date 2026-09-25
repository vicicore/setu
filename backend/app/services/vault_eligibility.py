"""Bridges the document vault (and, for the citizen-facing view, active
journeys) to the eligibility engine and the journey orchestrator. This
is the one place that turns "is this citizen's X actually verified" into
a set of service_codes — every other module (eligibility.py,
JourneyService) takes that set as an input rather than querying vault or
application state itself, so there is a single definition of what counts
as "verified" for orchestration purposes.

Convention: a document's `doc_type` is the service_code it satisfies
(e.g. a document with doc_type="income_certificate" satisfies the
income_certificate requirement). This mirrors the catalog seeded in
0002_seed_catalog.sql, where service codes are already the vocabulary
used everywhere else."""

from app.repositories.interfaces import ApplicationRepository, DocumentRepository
from app.schemas.enums import ApplicationStepStatus, DocumentStatus


def verified_service_codes_from_vault(
    citizen_id: str, document_repo: DocumentRepository
) -> set[str]:
    """Vault-only. Used to seed a *new* journey's starting state
    (start_or_reset_journey's already_verified_service_codes) — a fresh
    journey should only inherit pre-verified documents, not whatever a
    previous journey run happened to verify through a connector."""
    return {
        doc.doc_type
        for doc in document_repo.list_for_citizen(citizen_id)
        if doc.status == DocumentStatus.VERIFIED
    }


def verified_service_codes_for_citizen(
    citizen_id: str,
    document_repo: DocumentRepository,
    application_repo: ApplicationRepository,
) -> set[str]:
    """Vault + every active application's already-VERIFIED steps. This is
    what the citizen-facing eligibility view (GET
    /citizens/{id}/eligibility/{life_event_code}) uses — it must reflect
    reality even when a requirement was satisfied through a government
    connector mid-journey (e.g. income_certificate via Revenue) rather
    than sitting in the vault, or eligibility would visibly go stale the
    moment a connector approval came in. See docs/DECISIONS.md."""
    verified = verified_service_codes_from_vault(citizen_id, document_repo)
    for record in application_repo.list_for_citizen(citizen_id):
        for service_code, step in record.steps.items():
            if step.status == ApplicationStepStatus.VERIFIED:
                verified.add(service_code)
    return verified
