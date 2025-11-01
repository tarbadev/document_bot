from abc import ABC, abstractmethod

from langchain_core.documents import Document

from home.domain.file_metadata import FileMetadata


class DocumentRepository(ABC):
    @abstractmethod
    def upload_document(self, file_path: str, file_metadata: FileMetadata) -> list[Document]:
        pass