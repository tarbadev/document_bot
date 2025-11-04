from home.domain.question_validator import QuestionValidator


class CompositeQuestionValidator(QuestionValidator):
    def __init__(self, validators: list[QuestionValidator]):
        self.validators = validators

    def validate(self, question: str) -> None:
        for validator in self.validators:
            validator.validate(question)