from openai import OpenAI

from home.domain.invalid_question_error import InvalidQuestionError
from home.domain.question_validator import QuestionValidator


class OpenAIModerationValidator(QuestionValidator):
    def __init__(self, api_key: str, model: str = "omni-moderation-latest"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def validate(self, question: str) -> None:
        response = self.client.moderations.create(
            model=self.model,
            input=question
        )

        result = response.results[0]

        if result.flagged:
            categories = [cat for cat, flagged in result.categories.model_dump().items() if flagged]
            raise InvalidQuestionError(
                f"Question contains inappropriate content: {', '.join(categories)}"
            )