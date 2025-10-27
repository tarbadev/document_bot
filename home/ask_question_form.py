import time
from dataclasses import asdict
from typing import List

from django import forms
from langchain.chat_models import init_chat_model
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import CharacterTextSplitter
from langgraph.constants import START
from langgraph.graph import StateGraph

from document_bot.analytics import record_llm_call, debug
from home.messages_repository import add_message
from home.quoted_answer import QuotedAnswer
from home.repository import add_documents, vector_store
from home.state import State

LOCAL_STORAGE_PATH = "local_storage"

system_prompt = (
    "You're a helpful AI assistant. Given a user question "
    "and a document, answer the user question."
    "\n\nHere is the document: "
    "{context}"
)
model = "gpt-4o-mini"
llm = init_chat_model(model, model_provider="openai")

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{question}"),
    ]
)


def load_and_chunk_document(file):
    file_path = f"{LOCAL_STORAGE_PATH}/{file.name}"
    with open(file_path, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=15)
    chunks = text_splitter.split_documents(TextLoader(file_path).load())

    return chunks


def format_docs_with_id(docs: List[Document]) -> str:
    formatted = [
        f"Source ID: {i}\nArticle Snippet: {doc.page_content}"
        for i, doc in enumerate(docs)
    ]
    return "\n\n" + "\n\n".join(formatted)


def retrieve(state: State):
    retrieved_docs = vector_store.similarity_search(state["question"])
    return {"context": retrieved_docs}


def generate(state: State):
    formatted_docs = format_docs_with_id(state["context"])
    prompt_value = prompt.invoke({"question": state["question"], "context": formatted_docs})
    structured_llm = llm.with_structured_output(QuotedAnswer)

    t0 = time.perf_counter()
    ok = True
    prompt_tokens = completion_tokens = total_tokens = None

    try:
        response = structured_llm.invoke(prompt_value)
        usage = getattr(response, "usage", None)
        if usage:
            prompt_tokens = getattr(usage, "prompt_tokens", None)
            completion_tokens = getattr(usage, "completion_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)
        return {"answer": response}
    except Exception:
        ok = False
        raise
    finally:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        tokens = None
        if total_tokens is not None:
            tokens = {
                "prompt": prompt_tokens or 0,
                "completion": completion_tokens or 0,
                "total": total_tokens or 0
            }
        record_llm_call(model=model, ok=ok, duration_ms=dt_ms, tokens=tokens)


class AskQuestionForm(forms.Form):
    file = forms.FileField(required=False)
    question = forms.CharField(label="Question:", widget=forms.TextInput(attrs={'placeholder': 'Type a question.'}))

    def upload_and_ask_question(self, file):
        question = self.cleaned_data["question"]
        add_message('user', question)

        if file:
            chunks = load_and_chunk_document(file)
            add_documents(chunks)

        graph_builder = StateGraph(State).add_sequence([retrieve, generate])
        graph_builder.add_edge(START, "retrieve")
        graph = graph_builder.compile()

        result = graph.invoke({"question": question})

        debug("upload_and_ask_question",
              {
                  "question": question,
                  "source": [doc.metadata["source"] for doc in result["context"]],
                  "answer": asdict(result['answer'])
              })

        add_message('assistant', result["answer"].to_string())
