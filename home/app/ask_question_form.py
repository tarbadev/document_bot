import os

from django import forms

from home.domain.ai_assistant import AiAssistant
from home.domain.composite_question_validator import CompositeQuestionValidator
from home.domain.file_uploader import FileUploader
from home.domain.max_length_validator import MaxLengthValidator
from home.infrastructure.open_ai_metadata_extractor import OpenAIMetadataExtractor
from home.infrastructure.openai_moderation_validator import OpenAIModerationValidator
from home.infrastructure.pinecone_document_repository import PineconeDocumentRepository
from home.messages_repository import add_message

LOCAL_STORAGE_PATH = "local_storage"

question_validator = CompositeQuestionValidator([
    MaxLengthValidator(max_length=1000),
    OpenAIModerationValidator(api_key=os.environ.get("OPENAI_API_KEY"))
])


class AskQuestionForm(forms.Form):
    document_repository = PineconeDocumentRepository(api_key=os.environ.get("PINECONE_API_KEY"),
                                                     index_name="document-bot")
    ai_assistant = AiAssistant(
        document_repository=document_repository,
        question_validator=question_validator,
    )
    file_uploader = FileUploader(
        OpenAIMetadataExtractor(api_key=os.environ.get("OPENAI_API_KEY")),
        document_repository,
    )
    file = forms.FileField(required=False)
    question = forms.CharField(label="Question:", widget=forms.TextInput(attrs={'placeholder': 'Type a question.'}))

    def upload_and_ask_question(self, file, user_id=None):
        question = self.cleaned_data["question"]
        add_message('user', question)

        new_document = None
        if file:
            new_document = self.file_uploader.upload_file(f"{LOCAL_STORAGE_PATH}/{file.name}")

        answer = self.ai_assistant.answer(question, new_document, user_id=user_id)

        add_message('assistant', answer)
