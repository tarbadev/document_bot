from typing import TypedDict

from langchain_core.documents import Document

from home.quoted_answer import QuotedAnswer


class State(TypedDict):
    existing_documents: list[Document]
    question: str
    new_document: list[Document]
    answer: QuotedAnswer
