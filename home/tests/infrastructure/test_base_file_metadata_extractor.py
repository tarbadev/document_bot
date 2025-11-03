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
        actual = self.subject.extract_metadata(UPLOAD_FILE_PATH)
        
        expected = UPLOAD_BASE_FILE_METADATA
        self.assertEqual(expected, actual)