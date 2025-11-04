from home.domain.invalid_question_error import InvalidQuestionError
from home.domain.question_validator import QuestionValidator


class MaxLengthValidator(QuestionValidator):
    def __init__(self, max_length: int = 1000):
        self.max_length = max_length

    def validate(self, question: str) -> None:
        if len(question) > self.max_length:
            raise InvalidQuestionError(
                f"Question is too long. Maximum length is {self.max_length} characters."
            )