import time
from typing import Optional

from openai import OpenAI

from document_bot.analytics import record_validation_event
from home.domain.invalid_question_error import InvalidQuestionError
from home.domain.question_validator import QuestionValidator


class OpenAIModerationValidator(QuestionValidator):
    def __init__(self, api_key: str, model: str = "omni-moderation-latest"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def validate(self, question: str, user_id: Optional[str] = None) -> None:
        t0 = time.perf_counter()

        response = self.client.moderations.create(
            model=self.model,
            input=question
        )

        result = response.results[0]
        duration_ms = (time.perf_counter() - t0) * 1000.0

        if result.flagged:
            categories = [cat for cat, flagged in result.categories.model_dump().items() if flagged]
            reason = f"Question contains inappropriate content: {', '.join(categories)}"

            # Get category scores for metadata
            category_scores = {
                cat: score
                for cat, score in result.category_scores.model_dump().items()
                if cat in categories
            }

            record_validation_event(
                validator_name="openai_moderation",
                question=question,
                passed=False,
                duration_ms=duration_ms,
                reason=reason,
                user_id=user_id,
                meta={
                    "flagged_categories": categories,
                    "category_scores": category_scores,
                    "model": self.model
                }
            )
            raise InvalidQuestionError(reason)
        else:
            record_validation_event(
                validator_name="openai_moderation",
                question=question,
                passed=True,
                duration_ms=duration_ms,
                user_id=user_id,
                meta={"model": self.model}
            )