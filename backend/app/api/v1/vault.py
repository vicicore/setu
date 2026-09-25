from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.container import (
    get_application_repository,
    get_document_vault_service,
    get_journey_service,
)
from app.core.security import get_current_session, require_owner_or_admin
from app.repositories.models import DocumentRecord, SessionRecord
from app.schemas.document import DocumentRejectRequest, DocumentUsedByJourney, DocumentView
from app.services.document_service import DocumentNotFoundError, InvalidDocumentTransitionError
from app.services.life_event_catalog import get_life_event_meta
from app.services.vault_integration import (
    reject_document_and_sync_journeys,
    verify_document_and_sync_journeys,
)
from app.storage.local_disk import UnsupportedFileError

router = APIRouter(prefix="/citizens", tags=["vault"])


def _used_by(citizen_id: str, doc_type: str) -> list[DocumentUsedByJourney]:
    used_by = []
    for record in get_application_repository().list_for_citizen(citizen_id):
        if doc_type in record.steps:
            meta = get_life_event_meta(record.life_event_code)
            used_by.append(
                DocumentUsedByJourney(
                    application_id=record.id,
                    life_event_title_en=meta.title_en,
                    service_code=doc_type,
                )
            )
    return used_by


def _to_view(record: DocumentRecord, url: str) -> DocumentView:
    return DocumentView(
        id=record.id,
        citizen_id=record.citizen_id,
        doc_type=record.doc_type,
        issuer=record.issuer,
        original_filename=record.original_filename,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        status=record.status,
        rejection_reason=record.rejection_reason,
        url=url,
        created_at=record.created_at,
        updated_at=record.updated_at,
        used_by=_used_by(record.citizen_id, record.doc_type),
    )


def _get_owned_document(document_id: str, citizen_id: str, session: SessionRecord) -> DocumentRecord:
    """Fetches a document and verifies BOTH that the URL's citizen_id
    actually owns it AND that the authenticated session is that citizen
    (or admin) — a document_id alone is not proof of ownership, and a
    citizen_id in the URL is not proof of identity."""
    service = get_document_vault_service()
    try:
        record = service.get(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if record.citizen_id != citizen_id:
        raise HTTPException(status_code=404, detail="Document not found for this citizen")
    require_owner_or_admin(record.citizen_id, session)
    return record


@router.get("/{citizen_id}/documents", response_model=list[DocumentView])
def list_documents(
    citizen_id: str, session: SessionRecord = Depends(get_current_session)
) -> list[DocumentView]:
    require_owner_or_admin(citizen_id, session)
    service = get_document_vault_service()
    records = service.list_for_citizen(citizen_id)
    return [_to_view(r, service.get_url(r)) for r in records]


@router.post("/{citizen_id}/documents", response_model=DocumentView, status_code=201)
async def upload_document(
    citizen_id: str,
    doc_type: str = Form(...),
    issuer: str | None = Form(default=None),
    file: UploadFile = File(...),
    session: SessionRecord = Depends(get_current_session),
) -> DocumentView:
    require_owner_or_admin(citizen_id, session)
    service = get_document_vault_service()
    file_bytes = await file.read()
    try:
        record = service.upload(
            citizen_id=citizen_id,
            file_bytes=file_bytes,
            filename=file.filename or "upload",
            mime_type=file.content_type or "application/octet-stream",
            doc_type=doc_type,
            issuer=issuer,
        )
    except UnsupportedFileError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_view(record, service.get_url(record))


@router.get("/{citizen_id}/documents/{document_id}", response_model=DocumentView)
def get_document(
    citizen_id: str, document_id: str, session: SessionRecord = Depends(get_current_session)
) -> DocumentView:
    record = _get_owned_document(document_id, citizen_id, session)
    return _to_view(record, get_document_vault_service().get_url(record))


@router.post("/{citizen_id}/documents/{document_id}/submit-for-review", response_model=DocumentView)
def submit_document_for_review(
    citizen_id: str, document_id: str, session: SessionRecord = Depends(get_current_session)
) -> DocumentView:
    _get_owned_document(document_id, citizen_id, session)
    service = get_document_vault_service()
    try:
        record = service.submit_for_review(document_id)
    except (DocumentNotFoundError, InvalidDocumentTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_view(record, service.get_url(record))


@router.post("/{citizen_id}/documents/{document_id}/verify", response_model=DocumentView)
def verify_document(
    citizen_id: str, document_id: str, session: SessionRecord = Depends(get_current_session)
) -> DocumentView:
    """Simulated verification (there is no real department reviewer in
    this prototype) — but the transition is real backend state, and it
    cascades into any active journey through the same event-processing
    path a connector webhook uses. See app/services/vault_integration.py."""
    _get_owned_document(document_id, citizen_id, session)
    vault = get_document_vault_service()
    journeys = get_journey_service()
    try:
        record, _updated_journeys = verify_document_and_sync_journeys(document_id, vault, journeys)
    except (DocumentNotFoundError, InvalidDocumentTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_view(record, vault.get_url(record))


@router.post("/{citizen_id}/documents/{document_id}/reject", response_model=DocumentView)
def reject_document(
    citizen_id: str,
    document_id: str,
    body: DocumentRejectRequest,
    session: SessionRecord = Depends(get_current_session),
) -> DocumentView:
    """Mirrors verify_document: rejection cascades into any waiting
    journey step through the same event path, so the requirement
    visibly remains unsatisfied rather than silently stuck."""
    _get_owned_document(document_id, citizen_id, session)
    vault = get_document_vault_service()
    journeys = get_journey_service()
    try:
        record, _updated_journeys = reject_document_and_sync_journeys(
            document_id, body.reason, vault, journeys
        )
    except (DocumentNotFoundError, InvalidDocumentTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_view(record, vault.get_url(record))
