from unittest import TestCase
from unittest.mock import Mock, patch

from langchain_core.documents import Document
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice, ChatCompletion
from pinecone import ServerlessSpec

from home.infrastructure.pinecone_document_repository import PineconeDocumentRepository
from home.tests.test_factory import UPLOAD_FILE_PATH, UPLOAD_BASE_FILE_METADATA


class TestPineconeDocumentRepository(TestCase):
    api_key = "test_api_key"
    index_name = "document-bot"

    subject: PineconeDocumentRepository

    @patch('home.infrastructure.pinecone_document_repository.PineconeVectorStore')
    def setUp(self, mock_pinecone_vector_store_class):
        pinecone_patcher = patch('home.infrastructure.pinecone_document_repository.Pinecone')
        openai_embeddings_patcher = patch('home.infrastructure.pinecone_document_repository.OpenAIEmbeddings')

        mock_pinecone = pinecone_patcher.start()
        mock_openai_embeddings = openai_embeddings_patcher.start()

        self.mock_client = Mock()
        mock_pinecone.return_value = self.mock_client
        self.mock_index = Mock()
        self.mock_client.create_index.return_value = self.mock_index
        self.mock_client.Index.return_value = self.mock_index

        self.mock_embeddings = Mock()
        mock_openai_embeddings.return_value = self.mock_embeddings

        self.mock_vector_store = Mock()
        mock_pinecone_vector_store_class.return_value = self.mock_vector_store

        self.subject = PineconeDocumentRepository(self.api_key, self.index_name)

        self.addCleanup(pinecone_patcher.stop)
        self.addCleanup(openai_embeddings_patcher.stop)

        mock_pinecone.assert_called_once_with(api_key=self.api_key)
        self.mock_client.has_index.reset_mock()
        self.mock_client.Index.reset_mock()

    def test_init_returns_index_when_exists(self):
        self.mock_client.has_index.return_value = True

        PineconeDocumentRepository(self.api_key, self.index_name)

        self.mock_client.has_index.assert_called_once_with(self.index_name)
        self.mock_client.Index.assert_called_once_with(self.index_name)

    def test_init_returns_new_index_when_does_not_exists(self):
        self.mock_client.has_index.return_value = False

        PineconeDocumentRepository(self.api_key, self.index_name)

        self.mock_client.has_index.assert_called_once_with(self.index_name)
        self.mock_client.create_index.assert_called_once_with(
            name=self.index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    def _mock_response(self, content: str):
        mock_message = Mock(spec=ChatCompletionMessage)
        mock_message.content = content

        mock_choice = Mock(spec=Choice)
        mock_choice.message = mock_message

        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]

        return mock_response

    @patch('home.infrastructure.pinecone_document_repository.PineconeVectorStore.from_documents')
    @patch('home.infrastructure.pinecone_document_repository.RecursiveCharacterTextSplitter')
    def test_upload_document(
            self,
            mock_text_splitter_class,
            mock_vector_store_from_documents
    ):
        loaded_docs = [Document(page_content="Full document text", metadata={"source": "Frankenstein.txt"})]

        def mock_split_documents(docs):
            chunks = []
            for doc in docs:
                chunk1 = Document(page_content="This is chunk 1", metadata=doc.metadata.copy())
                chunk2 = Document(page_content="This is chunk 2", metadata=doc.metadata.copy())
                chunks.extend([chunk1, chunk2])
            return chunks

        mock_text_splitter = Mock()
        mock_text_splitter.split_documents.side_effect = mock_split_documents
        mock_text_splitter_class.return_value = mock_text_splitter

        mock_vector_store = Mock()
        mock_vector_store_from_documents.return_value = mock_vector_store

        with patch.object(self.subject, 'load_document', return_value=loaded_docs):
            result = self.subject.upload_document(UPLOAD_FILE_PATH, UPLOAD_BASE_FILE_METADATA)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].page_content, "This is chunk 1")
        self.assertEqual(result[1].page_content, "This is chunk 2")

        mock_text_splitter_class.assert_called_once_with(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )

        mock_text_splitter.split_documents.assert_called_once_with(loaded_docs)

        mock_vector_store_from_documents.assert_called_once()
        call_kwargs = mock_vector_store_from_documents.call_args.kwargs
        self.assertEqual(call_kwargs['index_name'], self.index_name)
        self.assertEqual(len(call_kwargs['documents']), 2)

        for i, doc in enumerate(result):
            self.assertEqual(doc.metadata['file_name'], 'Frankenstein.txt')
            self.assertEqual(doc.metadata['file_path'], UPLOAD_FILE_PATH)
            self.assertEqual(doc.metadata['file_size'], 448929)
            self.assertEqual(doc.metadata['file_extension'], 'txt')
            self.assertEqual(doc.metadata['chunk_index'], i)
            self.assertEqual(doc.metadata['total_chunks'], 2)
            self.assertIn('chunk_text', doc.metadata)
            self.assertIn('created_time', doc.metadata)
            self.assertIn('modified_time', doc.metadata)
            self.assertIn('upload_time', doc.metadata)

    def test_similarity_search(
            self,
    ):
        question = "What is the meaning of life?"
        answer = [Document(page_content="42", metadata={"source": "Frankenstein.txt"})]

        self.mock_vector_store.similarity_search.return_value = answer

        actual = self.subject.similarity_search(question, 5)

        self.assertEqual(actual, answer)

        self.mock_vector_store.similarity_search.assert_called_once_with(question, 5)
