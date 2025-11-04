import os

from django import forms

from home.domain.ai_assistant import AiAssistant
from home.domain.file_uploader import FileUploader
from home.infrastructure.open_ai_metadata_extractor import OpenAIMetadataExtractor
from home.infrastructure.pinecone_document_repository import PineconeDocumentRepository
from home.messages_repository import add_message

LOCAL_STORAGE_PATH = "local_storage"

class AskQuestionForm(forms.Form):
    document_repository = PineconeDocumentRepository(api_key=os.environ.get("PINECONE_API_KEY"), index_name="document-bot")
    ai_assistant = AiAssistant(document_repository=document_repository)
    file_uploader = FileUploader(
        OpenAIMetadataExtractor(api_key=os.environ.get("OPENAI_API_KEY")),
        document_repository,
    )
    file = forms.FileField(required=False)
    question = forms.CharField(label="Question:", widget=forms.TextInput(attrs={'placeholder': 'Type a question.'}))

    def upload_and_ask_question(self, file):
        question = self.cleaned_data["question"]
        add_message('user', question)

        new_document = None
        if file:
            new_document = self.file_uploader.upload_file(f"{LOCAL_STORAGE_PATH}/{file.name}")

        answer = self.ai_assistant.answer(question, new_document)

        add_message('assistant', answer)
