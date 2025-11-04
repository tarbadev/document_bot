from typing import List

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from home.domain.document_repository import DocumentRepository
from home.domain.file_metadata import FileMetadata


class PineconeDocumentRepository(DocumentRepository):

    def __init__(self, api_key: str, index_name: str, openai_api_key: str = None):
        self.index_name = index_name
        self.pc = Pinecone(api_key=api_key)
        self.dimension = 1536

        if self.pc.has_index(index_name):
            self.index = self.pc.Index(index_name)
        else:
            self._create_index()
            self.index = self.pc.Index(index_name)

        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=openai_api_key)
        self.vector_store = PineconeVectorStore(
            index_name=index_name,
            embedding=self.embeddings
        )

    def _create_index(self):
        self.pc.create_index(
            name=self.index_name,
            dimension=self.dimension,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )

    def load_document(self, file_path: str) -> List[Document]:
        # path = Path(file_path)
        # extension = path.suffix.lower()

        # if extension == '.txt':
        loader = TextLoader(file_path, encoding='utf-8')
        # elif extension == '.pdf':
        #     loader = PyPDFLoader(file_path)
        # elif extension == '.docx':
        #     loader = Docx2txtLoader(file_path)
        # else:
        #     loader = TextLoader(file_path, encoding='utf-8')

        return loader.load()

    def upload_document(self, file_path: str, file_metadata: FileMetadata) -> List[Document]:
        documents = self.load_document(file_path)

        metadata_dict = {
            'file_name': file_metadata.file_name,
            'file_path': file_metadata.file_path,
            'file_size': file_metadata.file_size,
            'file_extension': file_metadata.file_extension,
            'created_time': file_metadata.created_time.isoformat(),
            'modified_time': file_metadata.modified_time.isoformat(),
            'upload_time': file_metadata.upload_time.isoformat(),
        }

        if file_metadata.title:
            metadata_dict['title'] = file_metadata.title
        if file_metadata.authors:
            metadata_dict['authors'] = ', '.join(file_metadata.authors)
        if file_metadata.published_date:
            metadata_dict['published_date'] = file_metadata.published_date.isoformat()
        if file_metadata.publication_year:
            metadata_dict['publication_year'] = file_metadata.publication_year
        if file_metadata.editor:
            metadata_dict['editor'] = file_metadata.editor
        if file_metadata.publisher:
            metadata_dict['publisher'] = file_metadata.publisher
        if file_metadata.category:
            metadata_dict['category'] = file_metadata.category
        if file_metadata.keywords:
            metadata_dict['keywords'] = ', '.join(file_metadata.keywords)
        if file_metadata.abstract:
            metadata_dict['abstract'] = file_metadata.abstract
        if file_metadata.language:
            metadata_dict['language'] = file_metadata.language
        if file_metadata.document_type:
            metadata_dict['document_type'] = file_metadata.document_type
        if file_metadata.subject_area:
            metadata_dict['subject_area'] = file_metadata.subject_area

        for doc in documents:
            doc.metadata.update(metadata_dict)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_documents(documents)

        for i, chunk in enumerate(chunks):
            chunk.metadata['chunk_index'] = i
            chunk.metadata['total_chunks'] = len(chunks)
            chunk.metadata['chunk_text'] = chunk.page_content[:500]

        PineconeVectorStore.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            index_name=self.index_name
        )

        return chunks

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        return self.vector_store.similarity_search(query, k)
