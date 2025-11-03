import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest import TestCase, skipUnless

from dotenv import load_dotenv
from langfuse import get_client

from home.infrastructure.open_ai_metadata_extractor import OpenAIMetadataExtractor
from home.tests.test_factory import BASE_DIR

load_dotenv()

SCORECARD_VERSION = "v1"

METRIC_WEIGHTS = {
    "title": 0.15,
    "authors": 0.15,
    "published_date": 0.05,
    "publication_year": 0.05,
    "category": 0.15,
    "keywords": 0.15,
    "document_type": 0.10,
    "subject_area": 0.10,
    "language": 0.05,
    "publisher": 0.0125,
    "editor": 0.0125,
    "abstract": 0.025,
}

assert abs(sum(METRIC_WEIGHTS.values()) - 1.0) < 0.001, f"Metric weights must sum to 1.0, got {sum(METRIC_WEIGHTS.values())}"

class MetadataTestCase:
    def __init__(self, name: str, file_path: str, expected_metadata: Dict[str, Any]):
        self.name = name
        self.file_path = file_path
        self.expected_metadata = expected_metadata
        self.document_id = Path(file_path).stem


def get_git_commit_sha() -> Optional[str]:
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]
    except Exception:
        pass
    return None


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

        self.commit_sha = get_git_commit_sha()
        self.model_name = "gpt-4o-mini"

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
            return 0.8
        return 0.0

    def evaluate_field(self, field_name: str, expected: Any, actual: Any) -> Dict[str, Any]:
        result = {
            "field": field_name,
            "expected": expected,
            "actual": actual,
            "match": False,
            "score": 0.0,
            "notes": "",
            "available": True,
        }

        if expected is None and actual is None:
            result["match"] = True
            result["score"] = 1.0
            result["notes"] = "Both None"
            result["available"] = False
            return result

        if expected is None or actual is None:
            result["match"] = False
            result["score"] = 0.0
            result["notes"] = f"One is None: expected={expected}, actual={actual}"
            result["available"] = actual is not None
            return result

        if isinstance(expected, str) and isinstance(actual, str):
            score = self.compare_strings_fuzzy(expected, actual)
            result["score"] = score
            result["match"] = score >= 0.8
            if score < 1.0:
                result["notes"] = f"Partial match (score: {score:.2f})"

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
            result["match"] = (expected == actual)
            result["score"] = 1.0 if result["match"] else 0.0
            if not result["match"]:
                result["notes"] = f"Integer mismatch: {expected} vs {actual}"

        elif isinstance(expected, datetime) and isinstance(actual, datetime):
            result["match"] = self.compare_dates(expected, actual)
            result["score"] = 1.0 if result["match"] else 0.0
            if not result["match"]:
                result["notes"] = f"Date mismatch: {expected.date()} vs {actual.date()}"

        elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            tolerance = 0.01
            result["match"] = abs(expected - actual) <= tolerance
            result["score"] = 1.0 if result["match"] else 0.0
            if not result["match"]:
                result["notes"] = f"Numeric difference: {abs(expected - actual)}"

        else:
            result["notes"] = f"Type mismatch: expected {type(expected).__name__}, got {type(actual).__name__}"
            result["available"] = False

        return result

    def calculate_weighted_score(self, field_results: List[Dict]) -> float:
        weighted_sum = 0.0
        total_weight = 0.0

        for result in field_results:
            field_name = result["field"]
            if not result["available"]:
                continue

            weight = METRIC_WEIGHTS.get(field_name, 0.0)
            weighted_sum += result["score"] * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        normalized_score = (weighted_sum / total_weight) * 100
        return normalized_score

    def run_test_case(self, test_case: MetadataTestCase):
        extracted_metadata = self.subject.extract_metadata(test_case.file_path)

        field_results = []
        content_fields = [
            "title", "authors", "published_date", "publication_year",
            "editor", "publisher", "category", "keywords", "abstract",
            "language", "document_type", "subject_area"
        ]
        
        with self.langfuse.start_as_current_span(
            name="metadata_extraction_evaluation",
            metadata={
                "scorecard_version": SCORECARD_VERSION,
                "dataset": "metadata_fixtures",
                "model": self.model_name,
                "document_id": test_case.document_id,
                "document_name": Path(test_case.file_path).name,
                "test_case": test_case.name,
                "commit_sha": self.commit_sha,
                "max_chars": 12000,
            },
        ) as span:
            span.update_trace(
                tags=[
                    "evaluation",
                    "metadata_extraction",
                    f"doc:{test_case.document_id}",
                    f"model:{self.model_name}",
                    f"version:{SCORECARD_VERSION}",
                ]
            )
            
            for field in content_fields:
                expected_value = test_case.expected_metadata.get(field)
                actual_value = getattr(extracted_metadata, field, None)
                field_result = self.evaluate_field(field, expected_value, actual_value)
                field_results.append(field_result)
                
                if field_result["available"]:
                    span.score(
                        name=f"metric_{field}",
                        value=field_result["score"],
                        comment=field_result["notes"] or ("Match" if field_result["match"] else "Mismatch"),
                    )
            
            overall_score = self.calculate_weighted_score(field_results)
            
            span.score(
                name="overall_score",
                value=overall_score / 100,
                comment=f"Weighted composite score (v{SCORECARD_VERSION})",
            )
            
            span.update(
                output={
                    "overall_score": overall_score,
                    "weights_used": METRIC_WEIGHTS,
                    "available_metrics": [r["field"] for r in field_results if r["available"]],
                    "na_metrics": [r["field"] for r in field_results if not r["available"]],
                }
            )
        
        self.print_results_table(test_case.name, field_results, overall_score)
        
        self.assertGreaterEqual(
            overall_score, 
            75,
            f"{test_case.name} scored {overall_score:.2f}%, expected at least 75% (version {SCORECARD_VERSION})"
        )
        
        return overall_score

    def print_results_table(self, test_name: str, field_results: List[Dict], overall_score: float):
        print(f"\n{'=' * 110}")
        print(f"Test: {test_name} (Scorecard {SCORECARD_VERSION})")
        print(f"{'=' * 110}")
        print(f"{'Field':<20} {'Weight':<10} {'Match':<8} {'Score':<8} {'Expected':<30} {'Actual':<30}")
        print("-" * 110)

        for result in field_results:
            field = result["field"]
            weight = METRIC_WEIGHTS.get(field, 0.0)
            match_str = "✓" if result["match"] else ("N/A" if not result["available"] else "✗")
            score_str = f"{result['score']:.2f}" if result["available"] else "N/A"
            weight_str = f"{weight:.3f}" if result["available"] else "N/A"
            expected_str = str(result["expected"])[:29] if result["expected"] is not None else "None"
            actual_str = str(result["actual"])[:29] if result["actual"] is not None else "None"

            print(f"{field:<20} {weight_str:<10} {match_str:<8} {score_str:<8} {expected_str:<30} {actual_str:<30}")

        print("-" * 110)
        print(f"Overall Weighted Score: {overall_score:.2f}% (threshold: 75%)")
        print(f"Scorecard Version: {SCORECARD_VERSION}\n")

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
                "keywords": ["climate modeling", "neural networks", "weather prediction", "deep learning",
                             "atmospheric science"],
                "abstract": None,
                "language": "English",
                "document_type": "Research Paper",
                "subject_area": "Environmental Science"
            }
        )
        self.run_test_case(test_case)