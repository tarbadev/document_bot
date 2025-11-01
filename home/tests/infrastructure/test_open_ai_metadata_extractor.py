import json
from unittest import TestCase
from unittest.mock import Mock, patch
from datetime import datetime
from freezegun import freeze_time

from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice, ChatCompletion

from home.infrastructure.open_ai_metadata_extractor import OpenAIMetadataExtractor
from home.tests.test_factory import UPLOAD_OPEN_AI_FILE_METADATA, UPLOAD_FILE_PATH, OPENAI_FILE_METADATA_JSON, FROZEN_UPLOAD_TIME


class TestOpenAIMetadataExtractor(TestCase):
    api_key = "test_api_key"

    subject: OpenAIMetadataExtractor

    def setUp(self):
        openai_patcher = patch('home.infrastructure.open_ai_metadata_extractor.OpenAI')
        mock_openai = openai_patcher.start()

        self.mock_client = Mock()
        mock_openai.return_value = self.mock_client

        self.subject = OpenAIMetadataExtractor(self.api_key)

        self.addCleanup(openai_patcher.stop)

        mock_openai.assert_called_once_with(api_key=self.api_key)

        with open(UPLOAD_FILE_PATH, 'r') as f:
            text_sample = f.read()

        self.prompt = f"""Analyze the following document and extract metadata. Return ONLY a valid JSON object with these fields:

        - title: The document title (string)
        - authors: List of author names (array of strings, empty array if none found)
        - published_date: Publication date in YYYY-MM-DD format (string, null if not found)
        - publication_year: Year of publication (string, null if not found)
        - editor: Editor name if mentioned (string, null if not found)
        - publisher: Publisher name if mentioned (string, null if not found)
        - category: Document category/type (e.g., "research paper", "technical report", "book chapter", "article", "manual") (string)
        - keywords: Key topics/themes (array of strings, 3-10 keywords)
        - abstract: Brief summary or abstract if present (string, max 500 chars, null if not found)
        - language: Document language (string, e.g., "English")
        - document_type: Type of document (e.g., "academic", "technical", "business", "legal") (string)
        - subject_area: Main subject area (e.g., "Computer Science", "Medicine", "Business") (string)

        Document text:
        {text_sample}

        Return only the JSON object, no other text."""

    def _mock_response(self, content: str):
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = content

        mock_choice = Mock(spec=Choice)
        mock_choice.message = mock_message

        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]

        return mock_response
    
    def _mock_file_stat(self):
        mock_stat = Mock()
        mock_stat.st_size = 448929
        mock_stat.st_ctime = datetime.fromisoformat("2025-10-29T22:54:45.146198").timestamp()
        mock_stat.st_mtime = datetime.fromisoformat("2025-10-02T16:37:12.290537").timestamp()
        return mock_stat

    @freeze_time(FROZEN_UPLOAD_TIME)
    @patch('pathlib.Path.stat')
    def test_extract_metadata(self, mock_stat):
        mock_stat.return_value = self._mock_file_stat()
        mock_response = self._mock_response(json.dumps(OPENAI_FILE_METADATA_JSON))
        self.mock_client.chat.completions.create.return_value = mock_response

        actual = self.subject.extract_metadata(UPLOAD_FILE_PATH)

        expected = UPLOAD_OPEN_AI_FILE_METADATA
        self.assertEqual(expected, actual)

        self.mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a metadata extraction assistant. Return only valid JSON."},
                {"role": "user", "content": self.prompt}
            ],
            temperature=0
        )

    @freeze_time(FROZEN_UPLOAD_TIME)
    @patch('pathlib.Path.stat')
    def test_extract_metadata_when_response_has_extra_text(self, mock_stat):
        mock_stat.return_value = self._mock_file_stat()
        response_text = f"""Sure! Here's the extracted metadata:

        {json.dumps(OPENAI_FILE_METADATA_JSON)}
        
        Hope this helps!"""
        mock_response = self._mock_response(response_text)
        self.mock_client.chat.completions.create.return_value = mock_response

        actual = self.subject.extract_metadata(UPLOAD_FILE_PATH)

        expected = UPLOAD_OPEN_AI_FILE_METADATA
        self.assertEqual(expected, actual)

        self.mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a metadata extraction assistant. Return only valid JSON."},
                {"role": "user", "content": self.prompt}
            ],
            temperature=0
        )
