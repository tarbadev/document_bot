import time
from typing import Optional

from document_bot.analytics import debug
from home.domain.invalid_question_error import InvalidQuestionError
from home.domain.question_validator import QuestionValidator


class CompositeQuestionValidator(QuestionValidator):
    def __init__(self, validators: list[QuestionValidator]):
        self.validators = validators

    def validate(self, question: str, user_id: Optional[str] = None) -> None:
        t0 = time.perf_counter()

        debug("validation_start", {
            "question_length": len(question),
            "num_validators": len(self.validators),
            "user_id": user_id
        })

        try:
            for validator in self.validators:
                validator.validate(question, user_id=user_id)

            duration_ms = (time.perf_counter() - t0) * 1000.0
            debug("validation_complete", {
                "passed": True,
                "duration_ms": round(duration_ms, 2),
                "num_validators": len(self.validators),
                "user_id": user_id
            })

        except InvalidQuestionError as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            # Extract validator name from the most recent validation event
            failed_validator = type(validator).__name__ if validator else "unknown"

            debug("validation_complete", {
                "passed": False,
                "duration_ms": round(duration_ms, 2),
                "failed_validator": failed_validator,
                "reason": str(e),
                "user_id": user_id
            })
            raise