from abc import abstractmethod, ABC

from home.domain.file_metadata import FileMetadata


class FileMetadataExtractor(ABC):
    @abstractmethod
    def extract_metadata(self, file_path: str, max_chars=8000) -> FileMetadata:
        """
        Extract metadata from text.

        Args:
            file_path: Absolute path to the file.
            max_chars: Maximum characters to send to LLM

        Returns:
            Dictionary of extracted metadata
        """
        pass
