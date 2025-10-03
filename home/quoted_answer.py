from typing import List

from pydantic import BaseModel, Field

from home.citation import Citation


class QuotedAnswer(BaseModel):
    """Answer the user question based only on the given sources, and cite the sources used."""

    answer: str = Field(
        ...,
        description="The answer to the user question, which is based only on the given sources.",
    )
    citations: List[Citation] = Field(
        ..., description="Citations from the given sources that justify the answer."
    )

    def to_string(self) -> str:
        citations_text = "\n\n".join([f'"{citation.quote}"' for citation in self.citations])
        return f"{self.answer}\n\n{citations_text}"
