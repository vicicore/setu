from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.container import get_document_vault_service
from app.repositories.models import DocumentRecord
from app.schemas.document import DocumentView
from app.services.document_service import DocumentNotFoundError
from app.storage.local_disk import UnsupportedFileError

router = APIRouter(prefix="/citizens", tags=["vault"])


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
        url=url,
        created_at=record.created_at,
    )


@router.get("/{citizen_id}/documents", response_model=list[DocumentView])
def list_documents(citizen_id: str) -> list[DocumentView]:
    service = get_document_vault_service()
    records = service.list_for_citizen(citizen_id)
    return [_to_view(r, service.get_url(r)) for r in records]


@router.post("/{citizen_id}/documents", response_model=DocumentView, status_code=201)
async def upload_document(
    citizen_id: str,
    doc_type: str = Form(...),
    issuer: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> DocumentView:
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
def get_document(citizen_id: str, document_id: str) -> DocumentView:
    service = get_document_vault_service()
    try:
        record = service.get(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if record.citizen_id != citizen_id:
        raise HTTPException(status_code=404, detail="Document not found for this citizen")
    return _to_view(record, service.get_url(record))
