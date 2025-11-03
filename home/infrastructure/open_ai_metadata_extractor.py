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
        file_path = Path(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _get_text_sample(self, text: str, max_chars: int = 12000) -> str:
        if len(text) <= max_chars:
            return text
        
        beginning_chars = int(max_chars * 0.6)
        end_chars = int(max_chars * 0.4)
        
        return text[:beginning_chars] + "\n\n[... middle content omitted ...]\n\n" + text[-end_chars:]

    def extract_metadata(self, file_path, max_chars=12000) -> FileMetadata:
        base_metadata = super().extract_metadata(file_path)

        if Path(file_path).stat().st_size == 0:
            return base_metadata

        file_content = self._extract_text_from_file(file_path)
        text_sample = self._get_text_sample(file_content, max_chars)

        prompt = f"""Extract metadata from this document. Analyze the content carefully to identify key themes and information.

Return ONLY a valid JSON object with these exact fields:

{{
  "title": "string - the document title",
  "authors": ["array of author names without titles"],
  "published_date": "YYYY-MM-DD or null",
  "publication_year": integer or null,
  "editor": "string or null",
  "publisher": "string or null",
  "category": "string - broad category",
  "keywords": ["3-10 strings - main themes and topics"],
  "abstract": "string - brief summary under 300 chars, or null",
  "language": "string - e.g. English",
  "document_type": "string - specific type",
  "subject_area": "string - main field"
}}

Field Guidelines:
- title: Extract or infer the document title
- authors: Full names without "Dr.", "Prof.", etc. For "Mary Wollstonecraft Shelley" use "Mary Shelley"
- published_date/publication_year: Use ORIGINAL publication date for reprints/classics
- category: Broad type like "Fiction", "Non-fiction", "Academic", "Technical"
- keywords: Identify main themes from content (e.g., for gothic horror: ["gothic", "horror", "science fiction", "monster", "creation", "ethics"])
- abstract: Summarize the main content/plot/purpose
- document_type: Specific type like "Novel", "Research Paper", "Tutorial", "Essay"
- subject_area: Field like "Literature", "Computer Science", "Environmental Science"

Examples:
- Classic novel: category="Fiction", document_type="Novel", subject_area="Literature"
- Research paper: category="Academic", document_type="Research Paper", subject_area="Computer Science"
- Technical guide: category="Technical", document_type="Tutorial", subject_area="Computer Science"

Document:
{text_sample}

JSON only:"""

        response = self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise metadata extraction system. Analyze documents and extract accurate metadata. Focus on identifying the true nature and themes of the content. Return only valid JSON."},
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
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    def _parse_int(self, value: str | int | None) -> Optional[int]:
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
