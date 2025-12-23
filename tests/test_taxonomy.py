"""Tests for taxonomy enforcement and validation."""

import json
from pathlib import Path

import pytest

from aigov_eval.taxonomy import (
    get_allowed_signal_ids,
    get_taxonomy_version,
    load_taxonomy,
    normalize_signal,
)


def test_taxonomy_loads():
    """Verify taxonomy loads successfully."""
    taxonomy = load_taxonomy()
    assert "version" in taxonomy
    assert "allowed_signal_ids" in taxonomy
    assert "signal_metadata" in taxonomy
    assert isinstance(taxonomy["allowed_signal_ids"], set)
    assert len(taxonomy["allowed_signal_ids"]) > 0


def test_taxonomy_version():
    """Verify taxonomy version is available."""
    version = get_taxonomy_version()
    assert version
    assert isinstance(version, str)


def test_allowed_signal_ids():
    """Verify allowed signal IDs are loaded."""
    allowed_ids = get_allowed_signal_ids()
    assert isinstance(allowed_ids, set)
    assert len(allowed_ids) > 0

    # Check some known canonical signals
    assert "lack_of_consent" in allowed_ids
    assert "inadequate_transparency" in allowed_ids
    assert "inadequate_dpo" in allowed_ids


def test_normalize_signal_canonical():
    """Test normalize_signal with canonical IDs."""
    # Canonical signals should pass through unchanged
    assert normalize_signal("lack_of_consent") == "lack_of_consent"
    assert normalize_signal("inadequate_dpo") == "inadequate_dpo"
    assert normalize_signal("rights_violation") == "rights_violation"


def test_normalize_signal_synonyms():
    """Test normalize_signal with known synonyms."""
    # Known synonyms should map to canonical IDs
    assert normalize_signal("dpo_absence") == "inadequate_dpo"
    assert normalize_signal("data_minimization_violation") == "data_minimization_breach"
    assert normalize_signal("excessive_data_retention") == "retention_violation"
    assert normalize_signal("subject_rights_denial") == "rights_violation"
    assert normalize_signal("cross_border_transfer_violation") == "international_transfer_violation"
    assert normalize_signal("automated_decision_making") == "profiling_without_safeguards"


def test_normalize_signal_unknown():
    """Test normalize_signal with unknown signals."""
    # Unknown signals should return None
    assert normalize_signal("completely_made_up_signal") is None
    assert normalize_signal("random_violation") is None
    assert normalize_signal("") is None


def test_calibration_cases_use_canonical_signals():
    """Verify all calibration cases use canonical taxonomy signal IDs."""
    cases_dir = Path("cases/calibration")
    assert cases_dir.exists(), "cases/calibration directory not found"

    case_files = sorted(cases_dir.glob("*.json"))
    assert len(case_files) >= 12, f"Expected at least 12 calibration cases, found {len(case_files)}"

    allowed_ids = get_allowed_signal_ids()

    for case_file in case_files:
        with open(case_file, "r", encoding="utf-8") as f:
            case = json.load(f)

        expected = case.get("expected_outcome", {})
        signals = expected.get("signals", [])

        for signal in signals:
            assert signal in allowed_ids, (
                f"{case_file.name}: expected_outcome.signals contains non-canonical signal '{signal}'. "
                f"Must be one of: {sorted(allowed_ids)}"
            )


def test_judge_validation_function():
    """Test that judge validation function works correctly."""
    from aigov_eval.judge import _validate_and_clean_signals

    # Test with all canonical signals
    result = _validate_and_clean_signals({
        "verdict": "VIOLATION",
        "signals": ["lack_of_consent", "inadequate_transparency"],
        "citations": [],
        "rationale": []
    })
    assert result["signals"] == ["lack_of_consent", "inadequate_transparency"]
    assert "other_signals" not in result

    # Test with synonyms
    result = _validate_and_clean_signals({
        "verdict": "VIOLATION",
        "signals": ["dpo_absence", "subject_rights_denial"],
        "citations": [],
        "rationale": []
    })
    assert result["signals"] == ["inadequate_dpo", "rights_violation"]
    assert "other_signals" not in result

    # Test with unknown signals
    result = _validate_and_clean_signals({
        "verdict": "VIOLATION",
        "signals": ["lack_of_consent", "made_up_signal", "another_fake"],
        "citations": [],
        "rationale": []
    })
    assert result["signals"] == ["lack_of_consent"]
    assert result["other_signals"] == ["made_up_signal", "another_fake"]

    # Test with mix of canonical, synonyms, and unknown
    result = _validate_and_clean_signals({
        "verdict": "VIOLATION",
        "signals": ["lack_of_consent", "dpo_absence", "fake_signal"],
        "citations": [],
        "rationale": []
    })
    assert "lack_of_consent" in result["signals"]
    assert "inadequate_dpo" in result["signals"]
    assert len(result["signals"]) == 2
    assert result["other_signals"] == ["fake_signal"]


def test_batch_summary_includes_taxonomy_metadata():
    """Test that batch summaries include taxonomy and framework metadata."""
    from aigov_eval.batch_runner import run_batch

    # Run a minimal batch test with mock judge
    batch_summary = run_batch(
        cases_dir="cases/calibration",
        repeats=1,
        output_root="outputs/test_taxonomy",
        mock_judge=True,
        target="scripted",
        debug=False,
    )

    # Verify metadata fields exist
    assert "batch_meta" in batch_summary
    batch_meta = batch_summary["batch_meta"]

    assert "framework_id" in batch_meta, "batch_meta missing framework_id"
    assert "taxonomy_version" in batch_meta, "batch_meta missing taxonomy_version"
    assert "rubric_id" in batch_meta, "batch_meta missing rubric_id"

    # Verify values are reasonable
    assert batch_meta["framework_id"] == "gdpr"
    assert batch_meta["taxonomy_version"] == get_taxonomy_version()
    assert batch_meta["rubric_id"] == "gdpr_phase0_v1"
