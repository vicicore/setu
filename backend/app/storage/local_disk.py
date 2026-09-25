import mimetypes
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.storage.interfaces import DocumentStoragePort, StoredFileRef


class UnsupportedFileError(ValueError):
    pass


class LocalDiskDocumentStorage(DocumentStoragePort):
    """Demo/dev document storage — writes under <local_data_dir>/documents/.
    Enforces the same MIME allow-list and size limit the security spec
    requires of the real Appwrite-backed implementation, so those rules
    are exercised now rather than added later as an afterthought."""

    def __init__(self, base_dir: str | None = None) -> None:
        settings = get_settings()
        self._base_dir = Path(base_dir or settings.local_data_dir) / "documents"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._max_bytes = settings.max_upload_mb * 1024 * 1024
        self._allowed_mime_types = set(settings.allowed_upload_mime_types)

    def save(self, file_bytes: bytes, filename: str, mime_type: str) -> StoredFileRef:
        if mime_type not in self._allowed_mime_types:
            raise UnsupportedFileError(f"MIME type {mime_type} is not allowed")
        if len(file_bytes) > self._max_bytes:
            raise UnsupportedFileError(
                f"File exceeds the {self._max_bytes // (1024 * 1024)}MB upload limit"
            )
        extension = mimetypes.guess_extension(mime_type) or ""
        storage_key = f"{uuid.uuid4().hex}{extension}"
        (self._base_dir / storage_key).write_bytes(file_bytes)
        return StoredFileRef(
            storage_key=storage_key,
            original_filename=filename,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
        )

    def get_url(self, storage_key: str) -> str:
        return f"/media/documents/{storage_key}"

    def delete(self, storage_key: str) -> None:
        path = self._base_dir / storage_key
        if path.exists():
            path.unlink()
