import json
from unittest import TestCase
from unittest.mock import Mock, patch
from datetime import datetime
from freezegun import freeze_time

from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice, ChatCompletion

from home.infrastructure.open_ai_metadata_extractor import OpenAIMetadataExtractor
from home.tests.test_factory import UPLOAD_OPEN_AI_FILE_METADATA, UPLOAD_FILE_PATH, OPENAI_FILE_METADATA_JSON, \
    FROZEN_UPLOAD_TIME, UPLOAD_EMPTY_FILE_PATH, UPLOAD_EMPTY_FILE_METADATA


class TestOpenAIMetadataExtractor(TestCase):
    api_key = "test_api_key"

    subject: OpenAIMetadataExtractor

    def setUp(self):
        openai_patcher = patch('home.infrastructure.open_ai_metadata_extractor.openai.OpenAI')
        mock_openai = openai_patcher.start()

        self.mock_client = Mock()
        mock_openai.return_value = self.mock_client

        self.subject = OpenAIMetadataExtractor(self.api_key)

        self.addCleanup(openai_patcher.stop)

        mock_openai.assert_called_once_with(api_key=self.api_key)

    def _mock_response(self, content: str):
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = content

        mock_choice = Mock(spec=Choice)
        mock_choice.message = mock_message

        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]

        return mock_response

    @freeze_time(FROZEN_UPLOAD_TIME)
    def test_extract_metadata(self):
        mock_response = self._mock_response(json.dumps(OPENAI_FILE_METADATA_JSON))
        self.mock_client.chat.completions.create.return_value = mock_response

        actual = self.subject.extract_metadata(UPLOAD_FILE_PATH)

        expected = UPLOAD_OPEN_AI_FILE_METADATA
        self.assertEqual(expected, actual)

        call_args = self.mock_client.chat.completions.create.call_args
        self.assertEqual(call_args.kwargs['model'], 'gpt-4o-mini')
        self.assertEqual(call_args.kwargs['temperature'], 0)
        self.assertEqual(call_args.kwargs['messages'][0]['role'], 'system')
        self.assertEqual(call_args.kwargs['messages'][1]['role'], 'user')
        self.assertIn('Extract metadata from this document', call_args.kwargs['messages'][1]['content'])

    @freeze_time(FROZEN_UPLOAD_TIME)
    def test_extract_metadata_when_file_is_empty(self):
        actual = self.subject.extract_metadata(UPLOAD_EMPTY_FILE_PATH)

        expected = UPLOAD_EMPTY_FILE_METADATA
        self.assertEqual(expected, actual)

        self.mock_client.chat.completions.create.assert_not_called()

    @freeze_time(FROZEN_UPLOAD_TIME)
    def test_extract_metadata_when_response_has_extra_text(self):
        response_text = f"""Sure! Here's the extracted metadata:

        {json.dumps(OPENAI_FILE_METADATA_JSON)}
        
        Hope this helps!"""
        mock_response = self._mock_response(response_text)
        self.mock_client.chat.completions.create.return_value = mock_response

        actual = self.subject.extract_metadata(UPLOAD_FILE_PATH)

        expected = UPLOAD_OPEN_AI_FILE_METADATA
        self.assertEqual(expected, actual)

        call_args = self.mock_client.chat.completions.create.call_args
        self.assertEqual(call_args.kwargs['model'], 'gpt-4o-mini')
        self.assertEqual(call_args.kwargs['temperature'], 0)
