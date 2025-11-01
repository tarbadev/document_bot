from unittest import TestCase
from unittest.mock import Mock

from langchain_core.documents import Document

from home.domain.file_uploader import FileUploader
from home.tests.test_factory import UPLOAD_FILE_PATH, UPLOAD_OPEN_AI_FILE_METADATA


class FileUploaderTest(TestCase):
    mock_file_metadata_extractor = Mock()
    mock_document_repository = Mock()
    subject = FileUploader(
        file_metadata_extractor=mock_file_metadata_extractor,
        document_repository=mock_document_repository,
    )

    def test_file_uploader(self):
        expected_documents = [Document("some test content")]

        self.mock_file_metadata_extractor.extract_metadata.return_value = UPLOAD_OPEN_AI_FILE_METADATA
        self.mock_document_repository.upload_document.return_value = expected_documents

        documents = self.subject.upload_file(UPLOAD_FILE_PATH)

        self.assertEqual(documents, expected_documents)

        self.mock_file_metadata_extractor.extract_metadata.assert_called_once_with(UPLOAD_FILE_PATH)
        self.mock_document_repository.upload_document.assert_called_once_with(UPLOAD_FILE_PATH, UPLOAD_OPEN_AI_FILE_METADATA)