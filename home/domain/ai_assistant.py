import time
import typing
from dataclasses import asdict
from typing import Union

from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.language_models import LanguageModelInput
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, START
from openai import BaseModel

from document_bot.analytics import debug, record_llm_call
from home.domain.state import State
from home.domain.vector_store import VectorStore
from home.quoted_answer import QuotedAnswer


def _format_sources(docs: list[Document]) -> str:
    if not docs:
        return ""

    sources = []
    for i, doc in enumerate(docs, 1):
        title = doc.metadata.get('title', 'No title')
        link = doc.metadata.get('link', '')
        sources.append(f"{i}. {title}\n   {link}" if link else f"{i}. {title}")

    return "Sources:\n" + "\n".join(sources)


model = "gpt-4o-mini"
model_provider = "openai"


class AiAssistant:
    vector_store: VectorStore
    llm: Runnable[LanguageModelInput, Union[typing.Dict, BaseModel]]

    def __init__(self, vector_store: VectorStore):
        self.graph = self._build_graph()
        self.vector_store = vector_store
        self.llm = (init_chat_model(model, model_provider=model_provider)
                    .with_structured_output(QuotedAnswer))

    def _build_graph(self):
        graph_builder = StateGraph(State).add_sequence([self.retrieve, self.generate])
        graph_builder.add_edge(START, "retrieve")
        return graph_builder.compile()

    def answer(self, question: str, new_document: list[Document]) -> str:
        result = self.graph.invoke({"question": question, "new_document": new_document})

        debug("answer",
              {
                  "question": question,
                  "source": [doc.metadata["source"] for doc in result["existing_documents"]],
                  "answer": asdict(result['answer'])
              })

        return result["answer"].to_string()

    def retrieve(self, state: State) -> dict:
        new_document = state["new_document"]
        docs = self.vector_store.similarity_search(state["question"])
        # [docs.remove(document) for document in new_document]
        return {"existing_documents": docs, "new_document": new_document}

    def generate(self, state: State) -> dict:
        existing_documents = "\n\n".join([
            f"[Source {i + 1}]\n{doc.page_content}"
            for i, doc in enumerate(state["existing_documents"])
        ])
        new_document = "\n\nNew document:\n: None\n"
        if state.get("new_document"):
            new_document = (
                "\n\nNew document:\n: \"\"\"\n" +
                "\n\n".join([
                    f"[Source {i + 1}]\n{doc.page_content}"
                    for i, doc in enumerate(state["new_document"])
                ]) +
                "\n\"\"\""
            )
        system_prompt = (
            "You're a helpful AI assistant. Given the existing documents you already know, a user's question "
            "and, sometimes, a new document, answer the user's question."
            "If the new document is just 'None', you should answer the question using only the existing documents."
            "\n\nExisting documents:\n: \"\"\"\n{existing_documents}\n\"\"\""
            "{new_document}"
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{question}"),
            ]
        )
        prompt_value = prompt.invoke({
            "question": state["question"],
            "existing_documents": existing_documents,
            "new_document": new_document,
        })

        t0 = time.perf_counter()
        ok = True
        prompt_tokens = completion_tokens = total_tokens = None

        try:
            response = self.llm.invoke(prompt_value)
            usage = getattr(response, "usage", None)
            if usage:
                prompt_tokens = getattr(usage, "prompt_tokens", None)
                completion_tokens = getattr(usage, "completion_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)
            # print("\n\n=================\n\n")
            # print(state)
            # print("\n\n=================\n\n")
            # _format_sources(state["existing_documents"])
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
