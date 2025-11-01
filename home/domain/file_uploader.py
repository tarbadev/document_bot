from langchain_core.documents import Document

from home.domain.document_repository import DocumentRepository
from home.domain.file_metadata_extractor import FileMetadataExtractor


class FileUploader:
    file_metadata_extractor: FileMetadataExtractor
    document_repository: DocumentRepository

    def __init__(self, file_metadata_extractor: FileMetadataExtractor, document_repository: DocumentRepository):
        self.file_metadata_extractor = file_metadata_extractor
        self.document_repository = document_repository

    def upload_file(self, file_path: str) -> list[Document]:
        file_metadata = self.file_metadata_extractor.extract_metadata(file_path)
        return self.document_repository.upload_document(file_path, file_metadata)