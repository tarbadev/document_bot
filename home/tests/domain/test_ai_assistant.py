from unittest import TestCase
from unittest.mock import Mock, patch

from home.domain.ai_assistant import AiAssistant, model, model_provider
from home.domain.document_repository import DocumentRepository
from home.domain.invalid_question_error import InvalidQuestionError
from home.domain.question_validator import QuestionValidator
from home.domain.quoted_answer import QuotedAnswer
from home.domain.state import State


class TestAIAssistant(TestCase):
    subject: AiAssistant

    @patch('home.domain.ai_assistant.init_chat_model')
    def setUp(self, mock_init_chat_model):
        mock_llm = Mock()
        mock_structured_output = Mock()
        mock_llm.with_structured_output.return_value = mock_structured_output
        self.mock_init_chat_model = mock_init_chat_model
        self.mock_init_chat_model.return_value = mock_llm

        self.mock_document_repository = Mock(spec_set=DocumentRepository)
        self.mock_validator = Mock(spec_set=QuestionValidator)
        self.subject = AiAssistant(
            document_repository=self.mock_document_repository,
            question_validator=self.mock_validator
        )

        self.mock_init_chat_model.assert_called_once_with(model, model_provider=model_provider)

    def test_retrieve(self):
        question = "What is the meaning of life?"
        initial_state: State = {
            "existing_documents": [],
            "question": question,
            "new_document": [],
            "answer": QuotedAnswer(answer="", citations=[])
        }
        documents = [Mock()]
        expected_state = initial_state.copy()
        expected_state["existing_documents"] = documents

        self.mock_document_repository.similarity_search.return_value = documents

        self.assertEqual(
            expected_state,
            self.subject.retrieve(initial_state),
        )

        self.mock_document_repository.similarity_search.assert_called_once_with(question)

    def test_answer_validates_question(self):
        question = "What is AI?"
        self.mock_document_repository.similarity_search.return_value = []

        mock_answer = QuotedAnswer(answer="AI is artificial intelligence", citations=[])
        self.subject.llm.invoke = Mock(return_value=mock_answer)

        self.subject.answer(question, [])

        self.mock_validator.validate.assert_called_once_with(question)

    def test_answer_raises_when_validation_fails(self):
        question = "This is a very long question" * 100
        self.mock_validator.validate.side_effect = InvalidQuestionError("Question too long")

        with self.assertRaises(InvalidQuestionError):
            self.subject.answer(question, [])

        self.mock_document_repository.similarity_search.assert_not_called()

    def test_generate_with_existing_documents_only(self):
        doc1 = Mock()
        doc1.page_content = "Content 1"
        doc2 = Mock()
        doc2.page_content = "Content 2"

        state: State = {
            "existing_documents": [doc1, doc2],
            "question": "What is this?",
            "new_document": [],
            "answer": QuotedAnswer(answer="", citations=[])
        }

        mock_answer = QuotedAnswer(answer="Answer", citations=[])
        self.subject.llm.invoke = Mock(return_value=mock_answer)

        result = self.subject.generate(state)

        self.assertEqual(result["answer"], mock_answer)

        call_args = self.subject.llm.invoke.call_args[0][0]
        prompt_text = str(call_args)

        self.assertIn("[Source 1]", prompt_text)
        self.assertIn("[Source 2]", prompt_text)
        self.assertIn("Content 1", prompt_text)
        self.assertIn("Content 2", prompt_text)

    def test_generate_with_new_document_uses_continuous_numbering(self):
        existing_doc = Mock()
        existing_doc.page_content = "Existing content"

        new_doc = Mock()
        new_doc.page_content = "New content"

        state: State = {
            "existing_documents": [existing_doc],
            "question": "What is this?",
            "new_document": [new_doc],
            "answer": QuotedAnswer(answer="", citations=[])
        }

        mock_answer = QuotedAnswer(answer="Answer", citations=[])
        self.subject.llm.invoke = Mock(return_value=mock_answer)

        result = self.subject.generate(state)

        call_args = self.subject.llm.invoke.call_args[0][0]
        prompt_text = str(call_args)

        self.assertIn("[Source 1]", prompt_text)
        self.assertIn("[Source 2]", prompt_text)
        self.assertIn("Existing content", prompt_text)
        self.assertIn("New content", prompt_text)

    def test_generate_with_multiple_existing_and_new_documents(self):
        existing_docs = [Mock(page_content=f"Existing {i}") for i in range(3)]
        new_docs = [Mock(page_content=f"New {i}") for i in range(2)]

        state: State = {
            "existing_documents": existing_docs,
            "question": "What is this?",
            "new_document": new_docs,
            "answer": QuotedAnswer(answer="", citations=[])
        }

        mock_answer = QuotedAnswer(answer="Answer", citations=[])
        self.subject.llm.invoke = Mock(return_value=mock_answer)

        result = self.subject.generate(state)

        call_args = self.subject.llm.invoke.call_args[0][0]
        prompt_text = str(call_args)

        self.assertIn("[Source 1]", prompt_text)
        self.assertIn("[Source 2]", prompt_text)
        self.assertIn("[Source 3]", prompt_text)
        self.assertIn("[Source 4]", prompt_text)
        self.assertIn("[Source 5]", prompt_text)