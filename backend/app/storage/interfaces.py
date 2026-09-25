"""Document storage port. The document vault (Master Prompt section 4E)
talks to this interface only. A LocalDiskDocumentStorage backs it today;
an AppwriteDocumentStorage implementation is added later without the
document service or API routes changing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoredFileRef:
    storage_key: str
    original_filename: str
    mime_type: str
    size_bytes: int


class DocumentStoragePort(ABC):
    @abstractmethod
    def save(self, file_bytes: bytes, filename: str, mime_type: str) -> StoredFileRef: ...

    @abstractmethod
    def get_url(self, storage_key: str) -> str: ...

    @abstractmethod
    def delete(self, storage_key: str) -> None: ...
