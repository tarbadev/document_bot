import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from unittest import TestCase, skipUnless

from langfuse import get_client

from home.infrastructure.open_ai_metadata_extractor import OpenAIMetadataExtractor
from home.tests.test_factory import BASE_DIR


class MetadataTestCase:
    def __init__(self, name: str, file_path: str, expected_metadata: Dict[str, Any]):
        self.name = name
        self.file_path = file_path
        self.expected_metadata = expected_metadata


@skipUnless(os.getenv('RUN_EVALUATION_TESTS') == 'true', "Evaluation tests only run in CI/CD")
class TestOpenAIMetadataExtractorEvaluation(TestCase):
    langfuse = get_client()

    def setUp(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.fail("OPENAI_API_KEY environment variable is not set. Set it to run evaluation tests.")
        
        self.subject = OpenAIMetadataExtractor(api_key=api_key)
        self.fixtures_dir = Path(BASE_DIR) / "tests" / "fixtures"
        
        if not self.fixtures_dir.exists():
            self.fail(f"Fixtures directory not found at {self.fixtures_dir}")
    
    def jaccard_similarity(self, list1: List[str], list2: List[str]) -> float:
        if not list1 and not list2:
            return 1.0
        if not list1 or not list2:
            return 0.0
        
        set1 = set([item.lower() for item in list1])
        set2 = set([item.lower() for item in list2])
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def compare_dates(self, date1: datetime, date2: datetime, tolerance_days: int = 1) -> bool:
        if date1 is None and date2 is None:
            return True
        if date1 is None or date2 is None:
            return False
        diff = abs((date1 - date2).days)
        return diff <= tolerance_days
    
    def compare_strings_fuzzy(self, str1: str, str2: str) -> float:
        s1_lower = str1.lower()
        s2_lower = str2.lower()
        
        if s1_lower == s2_lower:
            return 1.0
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 1.0
        return 0.0
    
    def evaluate_field(self, field_name: str, expected: Any, actual: Any) -> Dict[str, Any]:
        result = {
            "field": field_name,
            "expected": expected,
            "actual": actual,
            "match": False,
            "score": 0.0,
            "notes": ""
        }
        
        if expected is None and actual is None:
            result["match"] = True
            result["score"] = 1.0
            result["notes"] = "Both None"
            return result
        
        if expected is None or actual is None:
            result["match"] = False
            result["score"] = 0.0
            result["notes"] = f"One is None: expected={expected}, actual={actual}"
            return result
        
        if isinstance(expected, str) and isinstance(actual, str):
            score = self.compare_strings_fuzzy(expected, actual)
            result["score"] = score
            result["match"] = score >= 1.0
            if score < 1.0:
                result["notes"] = "String mismatch"
        
        elif isinstance(expected, list) and isinstance(actual, list):
            if field_name == "authors":
                expected_normalized = [name.replace("Dr. ", "").replace("Prof. ", "") for name in expected]
                score = self.jaccard_similarity(expected_normalized, actual)
            else:
                score = self.jaccard_similarity(expected, actual)
            result["score"] = score
            result["match"] = score >= 0.7
            result["notes"] = f"Jaccard similarity: {score:.2f}"
        
        elif isinstance(expected, int) and isinstance(actual, int):
            if expected == actual:
                result["match"] = True
                result["score"] = 1.0
            else:
                result["score"] = 0.0
                result["notes"] = "Integer mismatch"
        
        elif isinstance(expected, datetime) and isinstance(actual, datetime):
            if self.compare_dates(expected, actual):
                result["match"] = True
                result["score"] = 1.0
            else:
                result["score"] = 0.0
                result["notes"] = "Date mismatch"
        
        elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            tolerance = 0.01
            if abs(expected - actual) <= tolerance:
                result["match"] = True
                result["score"] = 1.0
            else:
                result["score"] = 0.0
                result["notes"] = f"Numeric difference: {abs(expected - actual)}"
        
        else:
            result["notes"] = f"Type mismatch: expected {type(expected)}, got {type(actual)}"
        
        return result
    
    def run_test_case(self, test_case: MetadataTestCase):
        extracted_metadata = self.subject.extract_metadata(test_case.file_path)
        
        field_results = []
        content_fields = [
            "title", "authors", "published_date", "publication_year",
            "editor", "publisher", "category", "keywords", "abstract",
            "language", "document_type", "subject_area"
        ]

        with self.langfuse.start_as_current_span(name="open_ai_metadata_extractor") as span:
            for field in content_fields:
                expected_value = test_case.expected_metadata.get(field)
                actual_value = getattr(extracted_metadata, field, None)
                field_result = self.evaluate_field(field, expected_value, actual_value)
                span.score(
                    name=field,
                    value=field_result["score"],
                    comment=field_result["notes"],
                )
                field_results.append(field_result)
        
        total_score = sum(r["score"] for r in field_results)
        max_score = len(field_results)
        overall_score = (total_score / max_score) * 100 if max_score > 0 else 0
        span.score_trace(
            name="overall_score",
            value=overall_score,
        )

        self.print_results_table(test_case.name, field_results, overall_score)
        
        self.assertGreaterEqual(overall_score, 85, 
                                f"{test_case.name} scored {overall_score:.2f}%, expected at least 85%")
        
        return overall_score
    
    def print_results_table(self, test_name: str, field_results: List[Dict], overall_score: float):
        print(f"\n{'='*100}")
        print(f"Test: {test_name}")
        print(f"{'='*100}")
        print(f"{'Field':<20} {'Match':<10} {'Score':<10} {'Expected':<30} {'Actual':<30}")
        print("-" * 100)
        
        for result in field_results:
            match_str = "✓" if result["match"] else "✗"
            score_str = f"{result['score']:.2f}"
            expected_str = str(result["expected"])[:29]
            actual_str = str(result["actual"])[:29]
            print(f"{result['field']:<20} {match_str:<10} {score_str:<10} {expected_str:<30} {actual_str:<30}")
        
        print("-" * 100)
        print(f"Overall Score: {overall_score:.2f}%\n")
    
    def test_frankenstein(self):
        test_case = MetadataTestCase(
            name="Frankenstein Novel",
            file_path=str(self.fixtures_dir / "Frankenstein.txt"),
            expected_metadata={
                "title": "Frankenstein; Or, The Modern Prometheus",
                "authors": ["Mary Shelley"],
                "published_date": datetime(1818, 1, 1),
                "publication_year": 1818,
                "editor": None,
                "publisher": "Project Gutenberg",
                "category": "Fiction",
                "keywords": ["frankenstein", "monster", "creation", "science", "gothic", "horror"],
                "abstract": None,
                "language": "English",
                "document_type": "Novel",
                "subject_area": "Literature"
            }
        )
        self.run_test_case(test_case)
    
    def test_markdown_tutorial(self):
        test_case = MetadataTestCase(
            name="Markdown Tutorial",
            file_path=str(self.fixtures_dir / "ml_tutorial.md"),
            expected_metadata={
                "title": "Introduction to Machine Learning",
                "authors": ["Sarah Johnson"],
                "published_date": datetime(2024, 3, 15),
                "publication_year": 2024,
                "editor": None,
                "publisher": None,
                "category": "Non-fiction",
                "keywords": ["machine learning", "neural networks", "deep learning", "AI"],
                "abstract": None,
                "language": "English",
                "document_type": "Tutorial",
                "subject_area": "Computer Science"
            }
        )
        self.run_test_case(test_case)
    
    def test_research_paper(self):
        test_case = MetadataTestCase(
            name="Research Paper",
            file_path=str(self.fixtures_dir / "research_paper.txt"),
            expected_metadata={
                "title": "Neural Networks for Climate Prediction",
                "authors": ["Emily Chen", "Michael Rodriguez", "Aisha Patel"],
                "published_date": datetime(2024, 1, 15),
                "publication_year": 2024,
                "editor": "Robert Thompson",
                "publisher": "Journal of Climate Science",
                "category": "Academic",
                "keywords": ["climate modeling", "neural networks", "weather prediction", "deep learning", "atmospheric science"],
                "abstract": None,
                "language": "English",
                "document_type": "Research Paper",
                "subject_area": "Environmental Science"
            }
        )
        self.run_test_case(test_case)
