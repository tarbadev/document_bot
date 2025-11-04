import time
from typing import Optional

from document_bot.analytics import record_validation_event
from home.domain.invalid_question_error import InvalidQuestionError
from home.domain.question_validator import QuestionValidator


class MaxLengthValidator(QuestionValidator):
    def __init__(self, max_length: int = 1000):
        self.max_length = max_length

    def validate(self, question: str, user_id: Optional[str] = None) -> None:
        t0 = time.perf_counter()
        actual_length = len(question)
        passed = actual_length <= self.max_length

        if passed:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            record_validation_event(
                validator_name="max_length",
                question=question,
                passed=True,
                duration_ms=duration_ms,
                user_id=user_id,
                meta={"actual_length": actual_length, "max_length": self.max_length}
            )
        else:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            reason = f"Question is too long. Maximum length is {self.max_length} characters."
            record_validation_event(
                validator_name="max_length",
                question=question,
                passed=False,
                duration_ms=duration_ms,
                reason=reason,
                user_id=user_id,
                meta={"actual_length": actual_length, "max_length": self.max_length}
            )
            raise InvalidQuestionError(reason)