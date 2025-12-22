#!/usr/bin/env python3
"""
Import GDPR & AI Cases from PDF dataset into runnable eval artifacts.

This script converts the GDPR & AI Cases and Guidance Dataset PDF into:
1. Golden set items (golden_set/gs_###.json)
2. Executable test cases (cases/gs_###__<qid>.json)

Usage:
    python tools/import_golden_set.py
    python tools/import_golden_set.py --start 1 --end 10
    python tools/import_golden_set.py --dry-run
    python tools/import_golden_set.py --validate
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# PDF parsing - try to use PyPDF2 if available, otherwise use manual fallback
try:
    import PyPDF2
    HAS_PDF_PARSER = True
except ImportError:
    HAS_PDF_PARSER = False
    print("Warning: PyPDF2 not available. Use 'pip install PyPDF2' for PDF parsing.", file=sys.stderr)


# Repository paths
REPO_ROOT = Path(__file__).parent.parent
SOURCES_DIR = REPO_ROOT / "sources"
GOLDEN_SET_DIR = REPO_ROOT / "golden_set"
CASES_DIR = REPO_ROOT / "cases"
TAXONOMY_PATH = REPO_ROOT / "taxonomy" / "signals.json"
PDF_PATH = SOURCES_DIR / "GDPR & AI Cases and Guidance Dataset.pdf"


class GDPRCitationResolver:
    """Resolves GDPR article and recital citations to local documentation paths."""

    # Pattern matches: Art. 5(1)(a), Article 32, Art. 6, Recital 39, etc.
    CITATION_PATTERN = re.compile(
        r"(?:Art(?:icle)?\.?\s*(\d+)(?:\((\d+)\))?(?:\(([a-z])\))?|Recital\s*(\d+))",
        re.IGNORECASE
    )

    @classmethod
    def parse_citation(cls, citation_text: str) -> List[Dict[str, Any]]:
        """Parse citation text into structured components."""
        citations = []
        for match in cls.CITATION_PATTERN.finditer(citation_text):
            if match.group(4):  # Recital
                citations.append({
                    "type": "recital",
                    "number": int(match.group(4)),
                    "raw": match.group(0)
                })
            else:  # Article
                citations.append({
                    "type": "article",
                    "number": int(match.group(1)),
                    "paragraph": match.group(2),
                    "subparagraph": match.group(3),
                    "raw": match.group(0)
                })
        return citations

    @classmethod
    def resolve_to_path(cls, citation: Dict[str, Any]) -> str:
        """Convert citation to local documentation path."""
        if citation["type"] == "recital":
            number = str(citation["number"]).zfill(3)
            return f"legal/eu/gdpr/recitals/{number}.md"
        else:  # article
            number = str(citation["number"]).zfill(2)
            path = f"legal/eu/gdpr/articles/{number}.md"

            # Add anchor for paragraph/subparagraph
            if citation["paragraph"]:
                anchor = citation["paragraph"]
                if citation["subparagraph"]:
                    anchor += citation["subparagraph"]
                path += f"#{anchor}"

            return path

    @classmethod
    def resolve_citations(cls, citation_texts: List[str]) -> List[str]:
        """Resolve list of citation texts to documentation paths."""
        paths = []
        for text in citation_texts:
            parsed = cls.parse_citation(text)
            for citation in parsed:
                path = cls.resolve_to_path(citation)
                if path not in paths:
                    paths.append(path)
        return paths


class TaxonomyValidator:
    """Validates violation signals against the taxonomy."""

    def __init__(self, taxonomy_path: Path):
        self.valid_signals = set()
        if taxonomy_path.exists():
            with open(taxonomy_path, "r", encoding="utf-8") as f:
                taxonomy = json.load(f)
                self.valid_signals = {s["id"] for s in taxonomy.get("signals", [])}

    def validate_signals(self, signals: List[str]) -> tuple[List[str], bool]:
        """
        Validate signals against taxonomy.
        Returns (signals, needs_human_fill).
        """
        if not signals:
            return signals, False

        unknown = [s for s in signals if s not in self.valid_signals]
        needs_fill = len(unknown) > 0

        if needs_fill:
            print(f"  Warning: Unknown signals: {unknown}", file=sys.stderr)

        return signals, needs_fill


class PDFParser:
    """Parse the GDPR dataset PDF into structured items."""

    @classmethod
    def parse_pdf(cls, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Parse PDF and extract case items.

        This is a placeholder implementation. The actual PDF structure
        will determine the parsing logic.
        """
        if not HAS_PDF_PARSER:
            print("ERROR: PyPDF2 required for PDF parsing. Install with: pip install PyPDF2", file=sys.stderr)
            print("Alternatively, create a manual JSON input file.", file=sys.stderr)
            return []

        if not pdf_path.exists():
            print(f"ERROR: PDF not found at {pdf_path}", file=sys.stderr)
            print("Please place 'GDPR & AI Cases and Guidance Dataset.pdf' in the sources/ directory.", file=sys.stderr)
            return []

        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"

            # Parse the text into structured items
            # This will need to be customized based on actual PDF structure
            items = cls._parse_text_to_items(text)
            return items

        except Exception as e:
            print(f"ERROR parsing PDF: {e}", file=sys.stderr)
            return []

    @classmethod
    def _parse_text_to_items(cls, text: str) -> List[Dict[str, Any]]:
        """
        Parse PDF text into structured case items.

        This is a heuristic parser that will need customization based on
        the actual PDF format. For now, it returns a sample structure
        demonstrating the expected format.
        """
        # TODO: Implement actual PDF parsing logic based on document structure
        # For now, return empty list - users should provide structured JSON input
        # or customize this parser for their specific PDF format

        print("WARNING: PDF text parsing not yet implemented for this document format.", file=sys.stderr)
        print("Please use the --input-json option to provide structured data.", file=sys.stderr)

        return []


class GoldenSetImporter:
    """Main importer for converting dataset into eval artifacts."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.validator = TaxonomyValidator(TAXONOMY_PATH)
        self.citation_resolver = GDPRCitationResolver()

    def import_from_pdf(self, pdf_path: Path, start: Optional[int] = None, end: Optional[int] = None) -> int:
        """Import cases from PDF."""
        items = PDFParser.parse_pdf(pdf_path)
        if not items:
            print("No items parsed from PDF. See errors above.", file=sys.stderr)
            return 0

        return self._process_items(items, start, end)

    def import_from_json(self, json_path: Path, start: Optional[int] = None, end: Optional[int] = None) -> int:
        """Import cases from structured JSON input."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", [])
        return self._process_items(items, start, end)

    def _process_items(self, items: List[Dict[str, Any]], start: Optional[int], end: Optional[int]) -> int:
        """Process and convert items to golden set and cases."""
        if start is not None:
            items = items[start - 1:]
        if end is not None:
            items = items[:end - start + 1 if start else end]

        count = 0
        for idx, item in enumerate(items, start=start or 1):
            try:
                self._process_item(item, idx)
                count += 1
            except Exception as e:
                print(f"ERROR processing item {idx}: {e}", file=sys.stderr)

        return count

    def _process_item(self, raw_item: Dict[str, Any], item_num: int):
        """Process a single item: create golden set file and case files."""
        item_id = f"gs_{item_num:03d}"

        # Build golden set item
        golden_item = self._build_golden_set_item(raw_item, item_id)

        # Write golden set file
        golden_path = GOLDEN_SET_DIR / f"{item_id}.json"
        self._write_json(golden_path, golden_item, f"Golden set {item_id}")

        # Create executable cases for each question
        for question in golden_item.get("questions", []):
            qid = question.get("question_id", "q1")
            case = self._build_executable_case(golden_item, question, item_id, qid)

            case_path = CASES_DIR / f"{item_id}__{qid}.json"
            self._write_json(case_path, case, f"Case {item_id}__{qid}")

    def _build_golden_set_item(self, raw_item: Dict[str, Any], item_id: str) -> Dict[str, Any]:
        """Build normalized golden set item from raw input."""
        metadata = raw_item.get("metadata", {})
        needs_human_fill = False

        # Check for missing required fields
        required_fields = ["authority", "jurisdiction"]
        for field in required_fields:
            if not metadata.get(field):
                needs_human_fill = True

        questions = []
        for q_idx, raw_q in enumerate(raw_item.get("questions", []), start=1):
            question = self._normalize_question(raw_q, q_idx)
            if question.get("needs_human_fill"):
                needs_human_fill = True
            questions.append(question)

        return {
            "item_id": item_id,
            "source": "GDPR & AI Cases and Guidance Dataset.pdf",
            "metadata": {
                "authority": metadata.get("authority"),
                "jurisdiction": metadata.get("jurisdiction"),
                "date": metadata.get("date"),
                "source_url": metadata.get("source_url"),
                "imported_at": self._utc_now(),
                "needs_human_fill": needs_human_fill
            },
            "case_description": raw_item.get("case_description", raw_item.get("description", "")),
            "questions": questions,
            "notes": raw_item.get("notes")
        }

    def _normalize_question(self, raw_q: Dict[str, Any], q_num: int) -> Dict[str, Any]:
        """Normalize a question from raw input."""
        signals = raw_q.get("expected_signals", [])
        validated_signals, signals_need_fill = self.validator.validate_signals(signals)

        citations = raw_q.get("gdpr_citations", [])
        needs_fill = signals_need_fill or not raw_q.get("question_text")

        return {
            "question_id": raw_q.get("question_id", f"q{q_num}"),
            "question_text": raw_q.get("question_text", ""),
            "expected_verdict": raw_q.get("expected_verdict", "UNCLEAR"),
            "expected_signals": validated_signals,
            "gdpr_citations": citations,
            "rationale": raw_q.get("rationale", []),
            "needs_human_fill": needs_fill
        }

    def _build_executable_case(
        self,
        golden_item: Dict[str, Any],
        question: Dict[str, Any],
        item_id: str,
        qid: str
    ) -> Dict[str, Any]:
        """Build executable case from golden set item and question."""
        metadata = golden_item.get("metadata", {})
        case_description = golden_item.get("case_description", "")
        question_text = question.get("question_text", "")

        # Build conversation turns
        turns = []
        if case_description:
            turns.append({
                "role": "user",
                "content": case_description
            })
        if question_text:
            turns.append({
                "role": "user",
                "content": question_text
            })

        # Resolve GDPR citations
        citation_texts = question.get("gdpr_citations", [])
        citation_links = self.citation_resolver.resolve_citations(citation_texts)

        return {
            "scenario_id": f"{item_id}__{qid}",
            "title": question_text[:80] + "..." if len(question_text) > 80 else question_text,
            "category": "GDPR_COMPLIANCE",
            "framework": "GDPR",
            "golden_set_ref": item_id,
            "question_id": qid,
            "metadata": {
                "authority": metadata.get("authority"),
                "jurisdiction": metadata.get("jurisdiction"),
                "date": metadata.get("date"),
                "source_url": metadata.get("source_url"),
                "imported_from": "GDPR & AI Cases and Guidance Dataset.pdf"
            },
            "role": "AI auditor evaluating GDPR compliance",
            "auditor_seed": "You are an AI governance auditor. Evaluate this scenario for GDPR compliance and identify any violations.",
            "turns": turns,
            "expected_outcome": {
                "verdict": question.get("expected_verdict", "UNCLEAR"),
                "signals": question.get("expected_signals", []),
                "gdpr_citations": citation_texts,
                "gdpr_citation_links": citation_links,
                "rationale": question.get("rationale", [])
            },
            "failure_criteria": "System fails if it does not identify the expected GDPR violations or produces incorrect verdict",
            "needs_human_fill": question.get("needs_human_fill", False) or metadata.get("needs_human_fill", False)
        }

    def _write_json(self, path: Path, data: Dict[str, Any], description: str):
        """Write JSON file with pretty formatting."""
        if self.dry_run:
            print(f"[DRY RUN] Would write {description} to {path}")
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False, ensure_ascii=False)

        print(f"✓ Wrote {description} to {path}")

    @staticmethod
    def _utc_now() -> str:
        """Return current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def validate_outputs(self) -> bool:
        """Validate existing golden set and case outputs."""
        print("Validating golden set files...")
        golden_files = sorted(GOLDEN_SET_DIR.glob("gs_*.json"))

        if not golden_files:
            print("No golden set files found.")
            return False

        valid = True
        for gf in golden_files:
            try:
                with open(gf, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Validate structure
                required = ["item_id", "source", "metadata", "questions"]
                for field in required:
                    if field not in data:
                        print(f"  ✗ {gf.name}: Missing field '{field}'")
                        valid = False

                # Validate questions
                for q in data.get("questions", []):
                    signals = q.get("expected_signals", [])
                    _, needs_fill = self.validator.validate_signals(signals)
                    if needs_fill:
                        print(f"  ⚠ {gf.name}: Question {q.get('question_id')} has unknown signals")

                print(f"  ✓ {gf.name}")

            except Exception as e:
                print(f"  ✗ {gf.name}: {e}")
                valid = False

        return valid


def create_sample_input():
    """Create a sample JSON input file for manual data entry."""
    sample = {
        "description": "Sample input format for GDPR cases. Replace with actual case data from PDF.",
        "items": [
            {
                "metadata": {
                    "authority": "EDPB",
                    "jurisdiction": "EU",
                    "date": "2024-03-15",
                    "source_url": "https://edpb.europa.eu/example"
                },
                "case_description": "A company collected user email addresses without clear consent mechanisms and used them for marketing purposes not disclosed at collection time.",
                "questions": [
                    {
                        "question_id": "q1",
                        "question_text": "Does this scenario constitute a GDPR violation?",
                        "expected_verdict": "VIOLATION",
                        "expected_signals": [
                            "lack_of_consent",
                            "inadequate_transparency",
                            "purpose_limitation_breach"
                        ],
                        "gdpr_citations": [
                            "Art. 5(1)(a)",
                            "Art. 6",
                            "Art. 13"
                        ],
                        "rationale": [
                            "Collection without clear consent violates lawfulness principle",
                            "Marketing use not disclosed violates transparency requirement",
                            "Purpose changed without legal basis violates purpose limitation"
                        ]
                    }
                ],
                "notes": None
            }
        ]
    }

    sample_path = SOURCES_DIR / "sample_input.json"
    sample_path.parent.mkdir(parents=True, exist_ok=True)

    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)

    print(f"Created sample input file: {sample_path}")
    print("Edit this file with your case data, then run:")
    print(f"  python tools/import_golden_set.py --input-json {sample_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Import GDPR & AI Cases from PDF/JSON into eval artifacts"
    )
    parser.add_argument(
        "--input-pdf",
        type=Path,
        default=PDF_PATH,
        help="Path to input PDF (default: sources/GDPR & AI Cases and Guidance Dataset.pdf)"
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        help="Path to structured JSON input (alternative to PDF)"
    )
    parser.add_argument(
        "--start",
        type=int,
        help="Start at item number (1-indexed)"
    )
    parser.add_argument(
        "--end",
        type=int,
        help="End at item number (1-indexed)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing golden set outputs"
    )
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create a sample JSON input file template"
    )

    args = parser.parse_args()

    if args.create_sample:
        create_sample_input()
        return 0

    importer = GoldenSetImporter(dry_run=args.dry_run)

    if args.validate:
        valid = importer.validate_outputs()
        return 0 if valid else 1

    if args.input_json:
        if not args.input_json.exists():
            print(f"ERROR: Input JSON not found: {args.input_json}", file=sys.stderr)
            return 1
        count = importer.import_from_json(args.input_json, args.start, args.end)
    else:
        count = importer.import_from_pdf(args.input_pdf, args.start, args.end)

    if count > 0:
        print(f"\n✓ Successfully processed {count} items")
        if args.dry_run:
            print("  (dry run - no files written)")
        return 0
    else:
        print("\n✗ No items processed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
