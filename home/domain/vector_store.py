from abc import ABC, abstractmethod

from langchain_core.documents import Document


class VectorStore(ABC):
    @abstractmethod
    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        pass
