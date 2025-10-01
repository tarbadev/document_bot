from typing import List

from django import forms
from langchain.chat_models import init_chat_model
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langgraph.constants import START
from langgraph.graph import StateGraph

from home.quoted_answer import QuotedAnswer
from home.state import State
from home.views import add_to_messages

LOCAL_STORAGE_PATH = "local_storage"

system_prompt = (
    "You're a helpful AI assistant. Given a user question "
    "and a document, answer the user question."
    "\n\nHere is the document: "
    "{context}"
)

llm = init_chat_model("gpt-4o-mini", model_provider="openai")

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{question}"),
    ]
)
prompt.pretty_print()


def load_embeddings(chunks):
    db = Chroma.from_documents(chunks, OpenAIEmbeddings())

    return db.as_retriever()


def load_and_chunk_document(file):
    file_path = f"{LOCAL_STORAGE_PATH}/{file.name}"
    with open(file_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    chunks = text_splitter.split_documents(TextLoader(file_path).load())

    print(f"Chunks: {len(chunks)}")

    return chunks

def format_docs_with_id(docs: List[Document]) -> str:
    print(docs)
    formatted = [
        f"Source ID: {i}\nArticle Snippet: {doc.page_content}"
        for i, doc in enumerate(docs)
    ]
    return "\n\n" + "\n\n".join(formatted)

class AskQuestionForm(forms.Form):
    file = forms.FileField()
    question = forms.CharField()
    retriever = None

    def retrieve(self, state: State):
        retrieved_docs = self.retriever.invoke(state["question"])
        return {"context": retrieved_docs}

    @staticmethod
    def generate(state: State):
        formatted_docs = format_docs_with_id(state["context"])
        prompt_value = prompt.invoke({"question": state["question"], "context": formatted_docs})
        structured_llm = llm.with_structured_output(QuotedAnswer)
        response = structured_llm.invoke(prompt_value)
        return {"answer": response}

    def upload_and_ask_question(self, file):
        chunks = load_and_chunk_document(file)
        question = self.cleaned_data["question"]
        add_to_messages('user', question)

        self.retriever = load_embeddings(chunks)

        graph_builder = StateGraph(State).add_sequence([self.retrieve, self.generate])
        graph_builder.add_edge(START, "retrieve")
        graph = graph_builder.compile()

        result = graph.invoke({"question": question})

        sources = [doc.metadata["source"] for doc in result["context"]]
        print(f"Sources: {sources}\n\n")
        print(f"Answer: {result['answer']}")
        print(result["context"][0])

        add_to_messages('assistant', result["answer"].to_string())
