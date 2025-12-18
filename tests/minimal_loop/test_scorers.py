from pathlib import Path
import json

from aigov_eval.scorers import score_pii_disclosure, score_special_category_leak


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


def _load(name: str):
    path = FIXTURES / name
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_pii_scorer_detects_fixture():
    transcript = _load("transcript_pii.json")
    score = score_pii_disclosure(transcript)
    assert score["pass"] is False
    assert score["findings"], "Expected at least one PII finding"


def test_special_category_scorer_detects_fixture():
    transcript = _load("transcript_special.json")
    score = score_special_category_leak(transcript)
    assert score["pass"] is False
    assert score["findings"], "Expected at least one special-category finding"
