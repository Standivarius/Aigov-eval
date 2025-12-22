"""Tests for the golden set importer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add tools to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from import_golden_set import GDPRCitationResolver, TaxonomyValidator, GoldenSetImporter


class TestGDPRCitationResolver:
    """Test GDPR citation parsing and resolution."""

    def test_parse_simple_article(self):
        """Test parsing simple article reference."""
        citations = GDPRCitationResolver.parse_citation("Art. 6")
        assert len(citations) == 1
        assert citations[0]["type"] == "article"
        assert citations[0]["number"] == 6
        assert citations[0]["paragraph"] is None

    def test_parse_article_with_paragraph(self):
        """Test parsing article with paragraph."""
        citations = GDPRCitationResolver.parse_citation("Art. 5(1)")
        assert len(citations) == 1
        assert citations[0]["number"] == 5
        assert citations[0]["paragraph"] == "1"

    def test_parse_article_with_subparagraph(self):
        """Test parsing article with paragraph and subparagraph."""
        citations = GDPRCitationResolver.parse_citation("Art. 5(1)(a)")
        assert len(citations) == 1
        assert citations[0]["number"] == 5
        assert citations[0]["paragraph"] == "1"
        assert citations[0]["subparagraph"] == "a"

    def test_parse_recital(self):
        """Test parsing recital reference."""
        citations = GDPRCitationResolver.parse_citation("Recital 39")
        assert len(citations) == 1
        assert citations[0]["type"] == "recital"
        assert citations[0]["number"] == 39

    def test_parse_multiple_citations(self):
        """Test parsing multiple citations in text."""
        text = "See Art. 5(1)(a) and Art. 6, also Recital 39"
        citations = GDPRCitationResolver.parse_citation(text)
        assert len(citations) == 3

    def test_resolve_article_to_path(self):
        """Test resolving article to documentation path."""
        citation = {
            "type": "article",
            "number": 6,
            "paragraph": None,
            "subparagraph": None
        }
        path = GDPRCitationResolver.resolve_to_path(citation)
        assert path == "legal/eu/gdpr/articles/06.md"

    def test_resolve_article_with_paragraph_to_path(self):
        """Test resolving article with paragraph to path."""
        citation = {
            "type": "article",
            "number": 5,
            "paragraph": "1",
            "subparagraph": "a"
        }
        path = GDPRCitationResolver.resolve_to_path(citation)
        assert path == "legal/eu/gdpr/articles/05.md#1a"

    def test_resolve_recital_to_path(self):
        """Test resolving recital to documentation path."""
        citation = {
            "type": "recital",
            "number": 39
        }
        path = GDPRCitationResolver.resolve_to_path(citation)
        assert path == "legal/eu/gdpr/recitals/039.md"

    def test_resolve_citations_list(self):
        """Test resolving list of citation texts."""
        citations = ["Art. 5(1)(a)", "Art. 6", "Recital 39"]
        paths = GDPRCitationResolver.resolve_citations(citations)

        assert "legal/eu/gdpr/articles/05.md#1a" in paths
        assert "legal/eu/gdpr/articles/06.md" in paths
        assert "legal/eu/gdpr/recitals/039.md" in paths

    def test_resolve_deduplicates_paths(self):
        """Test that resolver deduplicates identical paths."""
        citations = ["Art. 6", "Article 6"]
        paths = GDPRCitationResolver.resolve_citations(citations)
        assert len(paths) == 1


class TestTaxonomyValidator:
    """Test taxonomy validation."""

    @pytest.fixture
    def sample_taxonomy_file(self, tmp_path):
        """Create a sample taxonomy file."""
        taxonomy = {
            "signals": [
                {"id": "lack_of_consent"},
                {"id": "inadequate_transparency"},
                {"id": "excessive_data_collection"}
            ]
        }
        taxonomy_path = tmp_path / "taxonomy.json"
        with open(taxonomy_path, "w") as f:
            json.dump(taxonomy, f)
        return taxonomy_path

    def test_validate_known_signals(self, sample_taxonomy_file):
        """Test validation of known signals."""
        validator = TaxonomyValidator(sample_taxonomy_file)
        signals = ["lack_of_consent", "inadequate_transparency"]
        validated, needs_fill = validator.validate_signals(signals)

        assert validated == signals
        assert needs_fill is False

    def test_validate_unknown_signals(self, sample_taxonomy_file):
        """Test validation flags unknown signals."""
        validator = TaxonomyValidator(sample_taxonomy_file)
        signals = ["lack_of_consent", "unknown_signal"]
        validated, needs_fill = validator.validate_signals(signals)

        assert validated == signals
        assert needs_fill is True

    def test_validate_empty_signals(self, sample_taxonomy_file):
        """Test validation of empty signal list."""
        validator = TaxonomyValidator(sample_taxonomy_file)
        signals = []
        validated, needs_fill = validator.validate_signals(signals)

        assert validated == []
        assert needs_fill is False


class TestGoldenSetImporter:
    """Test the main importer functionality."""

    @pytest.fixture
    def sample_input_data(self):
        """Create sample input data."""
        return {
            "items": [
                {
                    "metadata": {
                        "authority": "EDPB",
                        "jurisdiction": "EU",
                        "date": "2024-03-15",
                        "source_url": "https://edpb.europa.eu/example"
                    },
                    "case_description": "Test case description",
                    "questions": [
                        {
                            "question_id": "q1",
                            "question_text": "Is this a violation?",
                            "expected_verdict": "VIOLATION",
                            "expected_signals": ["lack_of_consent"],
                            "gdpr_citations": ["Art. 6"],
                            "rationale": ["Test rationale"]
                        }
                    ]
                }
            ]
        }

    @pytest.fixture
    def sample_json_file(self, tmp_path, sample_input_data):
        """Create a sample JSON input file."""
        json_path = tmp_path / "sample.json"
        with open(json_path, "w") as f:
            json.dump(sample_input_data, f)
        return json_path

    def test_normalize_question(self):
        """Test question normalization."""
        importer = GoldenSetImporter(dry_run=True)
        raw_question = {
            "question_text": "Test question?",
            "expected_verdict": "VIOLATION",
            "expected_signals": ["lack_of_consent"],
            "gdpr_citations": ["Art. 6"],
            "rationale": ["Test reason"]
        }

        normalized = importer._normalize_question(raw_question, 1)

        assert normalized["question_id"] == "q1"
        assert normalized["question_text"] == "Test question?"
        assert normalized["expected_verdict"] == "VIOLATION"
        assert "lack_of_consent" in normalized["expected_signals"]

    def test_build_golden_set_item(self):
        """Test golden set item building."""
        importer = GoldenSetImporter(dry_run=True)
        raw_item = {
            "metadata": {
                "authority": "EDPB",
                "jurisdiction": "EU",
                "date": "2024-03-15"
            },
            "case_description": "Test case",
            "questions": [
                {
                    "question_text": "Test?",
                    "expected_verdict": "VIOLATION",
                    "expected_signals": ["lack_of_consent"],
                    "gdpr_citations": ["Art. 6"],
                    "rationale": []
                }
            ]
        }

        golden = importer._build_golden_set_item(raw_item, "gs_001")

        assert golden["item_id"] == "gs_001"
        assert golden["source"] == "GDPR & AI Cases and Guidance Dataset.pdf"
        assert golden["metadata"]["authority"] == "EDPB"
        assert len(golden["questions"]) == 1

    def test_build_executable_case(self):
        """Test executable case building."""
        importer = GoldenSetImporter(dry_run=True)
        golden_item = {
            "item_id": "gs_001",
            "metadata": {
                "authority": "EDPB",
                "jurisdiction": "EU",
                "date": "2024-03-15"
            },
            "case_description": "A company violated GDPR."
        }
        question = {
            "question_id": "q1",
            "question_text": "Is this a violation?",
            "expected_verdict": "VIOLATION",
            "expected_signals": ["lack_of_consent"],
            "gdpr_citations": ["Art. 6"],
            "rationale": ["Missing consent"]
        }

        case = importer._build_executable_case(golden_item, question, "gs_001", "q1")

        assert case["scenario_id"] == "gs_001__q1"
        assert case["category"] == "GDPR_COMPLIANCE"
        assert case["framework"] == "GDPR"
        assert case["golden_set_ref"] == "gs_001"
        assert len(case["turns"]) == 2
        assert case["expected_outcome"]["verdict"] == "VIOLATION"
        assert "lack_of_consent" in case["expected_outcome"]["signals"]
        assert len(case["expected_outcome"]["gdpr_citation_links"]) > 0

    def test_citation_resolution_in_case(self):
        """Test that GDPR citations are resolved in executable case."""
        importer = GoldenSetImporter(dry_run=True)
        golden_item = {
            "item_id": "gs_001",
            "metadata": {},
            "case_description": "Test"
        }
        question = {
            "question_id": "q1",
            "question_text": "Test?",
            "expected_verdict": "VIOLATION",
            "expected_signals": [],
            "gdpr_citations": ["Art. 5(1)(a)", "Recital 39"],
            "rationale": []
        }

        case = importer._build_executable_case(golden_item, question, "gs_001", "q1")

        links = case["expected_outcome"]["gdpr_citation_links"]
        assert "legal/eu/gdpr/articles/05.md#1a" in links
        assert "legal/eu/gdpr/recitals/039.md" in links

    def test_import_from_json_dry_run(self, tmp_path, sample_json_file):
        """Test importing from JSON in dry-run mode."""
        importer = GoldenSetImporter(dry_run=True)

        # Temporarily override output directories
        import import_golden_set
        original_golden = import_golden_set.GOLDEN_SET_DIR
        original_cases = import_golden_set.CASES_DIR

        try:
            import_golden_set.GOLDEN_SET_DIR = tmp_path / "golden_set"
            import_golden_set.CASES_DIR = tmp_path / "cases"

            count = importer.import_from_json(sample_json_file)
            assert count == 1

        finally:
            import_golden_set.GOLDEN_SET_DIR = original_golden
            import_golden_set.CASES_DIR = original_cases

    def test_missing_required_fields_sets_needs_human_fill(self):
        """Test that missing required fields set needs_human_fill flag."""
        importer = GoldenSetImporter(dry_run=True)
        raw_item = {
            "metadata": {},  # Missing authority, jurisdiction
            "case_description": "Test",
            "questions": [
                {
                    "question_text": "Test?",
                    "expected_verdict": "VIOLATION",
                    "expected_signals": [],
                    "gdpr_citations": [],
                    "rationale": []
                }
            ]
        }

        golden = importer._build_golden_set_item(raw_item, "gs_001")
        assert golden["metadata"]["needs_human_fill"] is True


class TestIntegration:
    """Integration tests for full import workflow."""

    def test_full_import_workflow(self, tmp_path):
        """Test complete workflow from JSON to output files."""
        # Create input data
        input_data = {
            "items": [
                {
                    "metadata": {
                        "authority": "EDPB",
                        "jurisdiction": "EU",
                        "date": "2024-03-15",
                        "source_url": "https://example.com"
                    },
                    "case_description": "Company collected emails without consent.",
                    "questions": [
                        {
                            "question_id": "q1",
                            "question_text": "Does this violate GDPR?",
                            "expected_verdict": "VIOLATION",
                            "expected_signals": ["lack_of_consent", "inadequate_transparency"],
                            "gdpr_citations": ["Art. 6", "Art. 13"],
                            "rationale": [
                                "No valid consent obtained",
                                "Transparency requirements not met"
                            ]
                        }
                    ]
                }
            ]
        }

        input_json = tmp_path / "input.json"
        with open(input_json, "w") as f:
            json.dump(input_data, f)

        # Set up output directories
        import import_golden_set
        original_golden = import_golden_set.GOLDEN_SET_DIR
        original_cases = import_golden_set.CASES_DIR
        original_taxonomy = import_golden_set.TAXONOMY_PATH

        try:
            golden_dir = tmp_path / "golden_set"
            cases_dir = tmp_path / "cases"
            taxonomy_path = tmp_path / "taxonomy.json"

            # Create minimal taxonomy
            taxonomy_path.parent.mkdir(exist_ok=True)
            with open(taxonomy_path, "w") as f:
                json.dump({
                    "signals": [
                        {"id": "lack_of_consent"},
                        {"id": "inadequate_transparency"}
                    ]
                }, f)

            import_golden_set.GOLDEN_SET_DIR = golden_dir
            import_golden_set.CASES_DIR = cases_dir
            import_golden_set.TAXONOMY_PATH = taxonomy_path

            # Run import
            importer = GoldenSetImporter(dry_run=False)
            count = importer.import_from_json(input_json)

            assert count == 1

            # Verify golden set file
            golden_file = golden_dir / "gs_001.json"
            assert golden_file.exists()

            with open(golden_file) as f:
                golden = json.load(f)

            assert golden["item_id"] == "gs_001"
            assert golden["metadata"]["authority"] == "EDPB"
            assert len(golden["questions"]) == 1

            # Verify case file
            case_file = cases_dir / "gs_001__q1.json"
            assert case_file.exists()

            with open(case_file) as f:
                case = json.load(f)

            assert case["scenario_id"] == "gs_001__q1"
            assert case["category"] == "GDPR_COMPLIANCE"
            assert len(case["turns"]) == 2
            assert case["expected_outcome"]["verdict"] == "VIOLATION"

            # Verify the case can be loaded by aigov_eval loader
            # (We'll just verify it's valid JSON with required fields)
            required_scenario_fields = ["scenario_id", "category", "turns"]
            for field in required_scenario_fields:
                assert field in case

        finally:
            import_golden_set.GOLDEN_SET_DIR = original_golden
            import_golden_set.CASES_DIR = original_cases
            import_golden_set.TAXONOMY_PATH = original_taxonomy


def test_sample_creation(tmp_path):
    """Test sample input file creation."""
    import import_golden_set
    original_sources = import_golden_set.SOURCES_DIR

    try:
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()
        import_golden_set.SOURCES_DIR = sources_dir

        import_golden_set.create_sample_input()

        sample_file = sources_dir / "sample_input.json"
        assert sample_file.exists()

        # Verify it's valid JSON
        with open(sample_file) as f:
            data = json.load(f)

        assert "items" in data
        assert len(data["items"]) > 0

    finally:
        import_golden_set.SOURCES_DIR = original_sources
