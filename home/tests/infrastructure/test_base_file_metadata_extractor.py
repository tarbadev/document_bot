from datetime import datetime
from unittest import TestCase
from unittest.mock import patch, Mock

from freezegun import freeze_time

from home.infrastructure.base_file_metadata_extractor import BaseFileMetadataExtractor
from home.tests.test_factory import UPLOAD_FILE_PATH, UPLOAD_BASE_FILE_METADATA, FROZEN_UPLOAD_TIME


class TestBaseFileMetadataExtractor(TestCase):
    subject = BaseFileMetadataExtractor()

    @freeze_time(FROZEN_UPLOAD_TIME)
    def test_extract_metadata(self):
        mock_stat = Mock()
        mock_stat.st_size = 448929
        mock_stat.st_ctime = datetime.fromisoformat("2025-10-29T22:54:45.146198").timestamp()
        mock_stat.st_mtime = datetime.fromisoformat("2025-10-02T16:37:12.290537").timestamp()
        
        with patch('pathlib.Path.stat', return_value=mock_stat):
            actual = self.subject.extract_metadata(UPLOAD_FILE_PATH)
        
        expected = UPLOAD_BASE_FILE_METADATA
        self.assertEqual(expected, actual)
