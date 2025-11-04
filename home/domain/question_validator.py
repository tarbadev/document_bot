from abc import ABC, abstractmethod


class QuestionValidator(ABC):
    @abstractmethod
    def validate(self, question: str) -> None:
        pass