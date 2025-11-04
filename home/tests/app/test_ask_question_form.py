import os
import django

from home.domain.ai_assistant import AiAssistant
from home.domain.file_uploader import FileUploader

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'document_bot.settings')
django.setup()

from django.test import TestCase
from unittest.mock import Mock, patch, call
from django.core.files.uploadedfile import SimpleUploadedFile

from home.app.ask_question_form import AskQuestionForm, LOCAL_STORAGE_PATH


class TestAskQuestionForm(TestCase):

    @patch('home.ask_question_form.add_message')
    def test_load_and_chunk_not_called_when_no_document(
        self, 
        mock_add_message,
    ):
        form_data = {'question': 'What is the meaning of life?'}
        
        form = AskQuestionForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        mock_ai_assistant = Mock(spec=AiAssistant)
        mock_ai_assistant.answer.return_value = '42'
        form.ai_assistant = mock_ai_assistant

        mock_file_uploader = Mock(spec=FileUploader)
        form.file_uploader = mock_file_uploader

        form.upload_and_ask_question(file=None)

        mock_file_uploader.upload_file.assert_not_called()
        mock_ai_assistant.answer.assert_called_once_with('What is the meaning of life?', None)
        mock_add_message.assert_has_calls([
            call('user', 'What is the meaning of life?'),
            call('assistant', '42')
        ])

    @patch('home.ask_question_form.add_message')
    def test_load_and_chunk_called_when_document_uploaded(
        self,
        mock_add_message,
    ):
        file_name = "test_document.txt"
        file_path = f"{LOCAL_STORAGE_PATH}/{file_name}"
        uploaded_file = SimpleUploadedFile(
            file_name,
            b"This is test content",
            content_type="text/plain"
        )

        form_data = {'question': 'What is this document about?'}
        mock_file_uploader = Mock(spec=FileUploader)
        uploaded_document_chunks = [Mock(), Mock()]
        mock_file_uploader.upload_file.return_value = uploaded_document_chunks

        form = AskQuestionForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        mock_ai_assistant = Mock(spec=AiAssistant)
        mock_ai_assistant.answer.return_value = 'It is about testing'
        form.ai_assistant = mock_ai_assistant
        form.file_uploader = mock_file_uploader

        form.upload_and_ask_question(file=uploaded_file)

        mock_file_uploader.upload_file.assert_called_once_with(file_path)
        mock_ai_assistant.answer.assert_called_once_with('What is this document about?', uploaded_document_chunks)
        mock_add_message.assert_has_calls([
            call('user', 'What is this document about?'),
            call('assistant', 'It is about testing')
        ])
