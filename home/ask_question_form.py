from django import forms
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter

from home.domain.ai_assistant import AiAssistant
from home.messages_repository import add_message
from home.repository import add_documents, vector_store

LOCAL_STORAGE_PATH = "local_storage"


def load_and_chunk_document(file):
    file_path = f"{LOCAL_STORAGE_PATH}/{file.name}"
    with open(file_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=15)
    chunks = text_splitter.split_documents(TextLoader(file_path).load())

    return chunks


class AskQuestionForm(forms.Form):
    ai_assistant = AiAssistant(vector_store=vector_store)
    file = forms.FileField(required=False)
    question = forms.CharField(label="Question:", widget=forms.TextInput(attrs={'placeholder': 'Type a question.'}))

    def upload_and_ask_question(self, file):
        question = self.cleaned_data["question"]
        add_message('user', question)

        new_document = None
        if file:
            new_document = load_and_chunk_document(file)
            add_documents(new_document)

        answer = self.ai_assistant.answer(question, new_document)

        add_message('assistant', answer)
