from datetime import datetime
from pathlib import Path

from home.domain.file_metadata import FileMetadata
from home.domain.file_metadata_extractor import FileMetadataExtractor


class BaseFileMetadataExtractor(FileMetadataExtractor):
    def extract_metadata(self, file_path: str, max_chars=8000) -> FileMetadata:
        file_path = Path(file_path)
        stat = file_path.stat()

        return FileMetadata(
            file_name=file_path.name,
            file_path=str(file_path.absolute()),
            file_size=stat.st_size,
            file_extension=file_path.suffix.lower().split(".")[-1],
            created_time=datetime.fromtimestamp(stat.st_ctime),
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            upload_time=datetime.now(),
        )