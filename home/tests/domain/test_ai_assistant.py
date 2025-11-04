from unittest import TestCase
from unittest.mock import Mock, patch

from home.domain.ai_assistant import AiAssistant, model, model_provider
from home.domain.document_repository import DocumentRepository
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
        self.subject = AiAssistant(document_repository=self.mock_document_repository)

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