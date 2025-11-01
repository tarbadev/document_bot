import os
from datetime import datetime
from pathlib import Path

from home.domain.file_metadata import FileMetadata

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_FILE_PATH = os.path.join(BASE_DIR, 'tests', 'fixtures', 'Frankenstein.txt')

FROZEN_UPLOAD_TIME = "2025-10-30T10:00:00.000000"

UPLOAD_BASE_FILE_METADATA = FileMetadata(
    file_name="Frankenstein.txt",
    file_path=UPLOAD_FILE_PATH,
    file_size=448929,
    file_extension="txt",
    created_time=datetime.fromisoformat("2025-10-29T22:54:45.146198"),
    modified_time=datetime.fromisoformat("2025-10-02T16:37:12.290537"),
    upload_time=datetime.fromisoformat(FROZEN_UPLOAD_TIME),
)
UPLOAD_OPEN_AI_FILE_METADATA = FileMetadata(
    file_name=UPLOAD_BASE_FILE_METADATA.file_name,
    file_path=UPLOAD_BASE_FILE_METADATA.file_path,
    file_size=UPLOAD_BASE_FILE_METADATA.file_size,
    file_extension=UPLOAD_BASE_FILE_METADATA.file_extension,
    created_time=UPLOAD_BASE_FILE_METADATA.created_time,
    modified_time=UPLOAD_BASE_FILE_METADATA.modified_time,
    upload_time=UPLOAD_BASE_FILE_METADATA.upload_time,
    title="Frankenstein",
    authors=["Mary Wollstonecraft (Godwin) Shelley"],
    published_date=datetime.fromisoformat("1993-10-01"),
    publication_year=1993,
    editor=None,
    publisher=None,
    category=None,
    keywords=["novel", "scary", "monster"],
    abstract="Story of Frankenstein, created by dr blah blah blah",
    language="english",
    document_type="novel",
    subject_area="N/A",
)

OPENAI_FILE_METADATA_JSON = {
    "title": "Frankenstein",
    "authors": ["Mary Wollstonecraft (Godwin) Shelley"],
    "published_date": "1993-10-01",
    "publication_year": "1993",
    "editor": None,
    "publisher": None,
    "category": None,
    "keywords": ["novel", "scary", "monster"],
    "abstract": "Story of Frankenstein, created by dr blah blah blah",
    "language": "english",
    "document_type": "novel",
    "subject_area": "N/A"
}
