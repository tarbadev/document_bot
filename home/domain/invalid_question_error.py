class InvalidQuestionError(Exception):
    """Exception raised when a question fails validation."""

    def __init__(self, message: str = "Invalid question"):
        self.message = message
        super().__init__(self.message)