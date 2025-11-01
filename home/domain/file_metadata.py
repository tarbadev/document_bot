from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FileMetadata:
    # file metadata
    file_name: str
    file_path: str
    file_size: float
    file_extension: str
    created_time: datetime
    modified_time: datetime
    upload_time: datetime

    # file content metadata
    title: str | None = None
    authors: list[str] = None
    published_date: datetime | None = None
    publication_year: int | None = None
    editor: str | None = None
    publisher: str | None = None
    category: str | None = None
    keywords: list[str] = None
    abstract: str | None = None
    language: str | None = None
    document_type: str | None = None
    subject_area: str | None = None