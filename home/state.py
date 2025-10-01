from typing import TypedDict

from langchain_core.documents import Document

from home.quoted_answer import QuotedAnswer


class State(TypedDict):
    question: str
    context: Document
    answer: QuotedAnswer