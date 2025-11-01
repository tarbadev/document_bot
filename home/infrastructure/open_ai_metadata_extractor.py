import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from langfuse import openai
from openai import OpenAI

from home.domain.file_metadata import FileMetadata
from home.infrastructure.base_file_metadata_extractor import BaseFileMetadataExtractor


class OpenAIMetadataExtractor(BaseFileMetadataExtractor):
    llm: OpenAI

    def __init__(self, api_key):
        self.llm = openai.OpenAI(
            api_key=api_key,
        )

    def _extract_text_from_file(self, file_path):
        """
        Extract text content from various file types.

        Args:
            file_path: Path to the file

        Returns:
            Extracted text content
        """
        file_path = Path(file_path)

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def extract_metadata(self, file_path, max_chars=8000) -> FileMetadata:
        base_metadata = super().extract_metadata(file_path)

        file_content = self._extract_text_from_file(file_path)
        text_sample = file_content

        prompt = f"""Analyze the following document and extract metadata. Return ONLY a valid JSON object with these fields:

        - title: The document title (string)
        - authors: List of author names (array of strings, empty array if none found)
        - published_date: Publication date in YYYY-MM-DD format (string, null if not found)
        - publication_year: Year of publication (string, null if not found)
        - editor: Editor name if mentioned (string, null if not found)
        - publisher: Publisher name if mentioned (string, null if not found)
        - category: Document category/type (e.g., "research paper", "technical report", "book chapter", "article", "manual") (string)
        - keywords: Key topics/themes (array of strings, 3-10 keywords)
        - abstract: Brief summary or abstract if present (string, max 500 chars, null if not found)
        - language: Document language (string, e.g., "English")
        - document_type: Type of document (e.g., "academic", "technical", "business", "legal") (string)
        - subject_area: Main subject area (e.g., "Computer Science", "Medicine", "Business") (string)

        Document text:
        {text_sample}

        Return only the JSON object, no other text."""

        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a metadata extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        response_text = response.choices[0].message.content

        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return self._json_to_file_metadata(
                base_metadata,
                json.loads(json_match.group()),
            )
        else:
            return self._json_to_file_metadata(
                base_metadata,
                json.loads(response_text),
            )

    def _parse_datetime(self, value: str | datetime | None) -> Optional[datetime]:
        """Parse datetime from string or return existing datetime"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    def _parse_int(self, value: str | int | None) -> Optional[int]:
        """Parse int from string or return existing int"""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        return int(value)

    def _json_to_file_metadata(self, base_metadata: FileMetadata, json_data) -> FileMetadata:
        return FileMetadata(
            file_name=base_metadata.file_name,
            file_path=base_metadata.file_path,
            file_size=base_metadata.file_size,
            file_extension=base_metadata.file_extension,
            created_time=base_metadata.created_time,
            modified_time=base_metadata.modified_time,
            upload_time=base_metadata.upload_time,
            title=json_data.get('title'),
            authors=json_data.get('authors'),
            published_date=self._parse_datetime(json_data.get('published_date')),
            publication_year=self._parse_int(json_data.get('publication_year')),
            editor=json_data.get('editor'),
            publisher=json_data.get('publisher'),
            category=json_data.get('category'),
            keywords=json_data.get('keywords'),
            abstract=json_data.get('abstract'),
            language=json_data.get('language'),
            document_type=json_data.get('document_type'),
            subject_area=json_data.get('subject_area'),
        )
