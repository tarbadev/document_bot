from abc import ABC, abstractmethod
from typing import Optional


class QuestionValidator(ABC):
    @abstractmethod
    def validate(self, question: str, user_id: Optional[str] = None) -> None:
        pass