"""Test taxonomy enforcement and signal validation."""

import json
import tempfile
from pathlib import Path

import pytest

from aigov_eval.taxonomy import (
    get_allowed_signal_ids,
    get_taxonomy_version,
    get_signal_metadata,
    normalize_signal,
    validate_signals,
    SIGNAL_SYNONYMS,
)
from aigov_eval.batch_runner import run_batch


def test_taxonomy_loads_correctly():
    """Test that taxonomy loads and has expected structure."""
    version = get_taxonomy_version()
    assert version is not None
    assert version != "unknown"

    allowed = get_allowed_signal_ids()
    assert len(allowed) > 0
    assert "lack_of_consent" in allowed
    assert "inadequate_transparency" in allowed


def test_all_calibration_signals_are_canonical():
    """Assert every expected_outcome.signal in calibration cases is in allowed_signal_ids."""
    allowed = get_allowed_signal_ids()
    cases_dir = Path("cases/calibration")

    invalid_signals = []
    for case_file in cases_dir.glob("*.json"):
        with open(case_file, encoding="utf-8") as f:
            case = json.load(f)

        expected = case.get("expected_outcome", {})
        signals = expected.get("signals", [])

        for signal in signals:
            if signal not in allowed:
                invalid_signals.append((case_file.name, signal))

    assert not invalid_signals, (
        f"Found non-canonical signals in calibration cases: {invalid_signals}"
    )


def test_signal_normalization():
    """Test signal normalization works correctly."""
    allowed = get_allowed_signal_ids()

    # Canonical signals pass through
    normalized, is_valid = normalize_signal("lack_of_consent", allowed)
    assert is_valid is True
    assert normalized == "lack_of_consent"

    # Synonyms are normalized
    normalized, is_valid = normalize_signal("data_minimization_violation", allowed)
    assert is_valid is True
    assert normalized == "data_minimization_breach"

    # Unknown signals fail
    normalized, is_valid = normalize_signal("completely_made_up_signal", allowed)
    assert is_valid is False
    assert normalized is None


def test_validate_signals_separates_valid_and_invalid():
    """Test validate_signals correctly separates valid from invalid signals."""
    allowed = get_allowed_signal_ids()

    result = validate_signals([
        "lack_of_consent",  # valid canonical
        "data_minimization_violation",  # valid synonym -> data_minimization_breach
        "made_up_signal",  # invalid
        "inadequate_security",  # valid canonical
    ], allowed)

    assert "lack_of_consent" in result["signals"]
    assert "data_minimization_breach" in result["signals"]
    assert "inadequate_security" in result["signals"]
    assert "made_up_signal" in result["other_signals"]
    assert len(result["signals"]) == 3
    assert len(result["other_signals"]) == 1


def test_validate_signals_removes_duplicates():
    """Test validate_signals removes duplicates after normalization."""
    allowed = get_allowed_signal_ids()

    result = validate_signals([
        "data_minimization_violation",  # -> data_minimization_breach
        "data_minimization_breach",  # same as above
    ], allowed)

    assert result["signals"] == ["data_minimization_breach"]
    assert len(result["other_signals"]) == 0


def test_synonyms_map_to_valid_signals():
    """Test all synonym mappings point to valid taxonomy signals."""
    allowed = get_allowed_signal_ids()

    invalid_mappings = []
    for synonym, canonical in SIGNAL_SYNONYMS.items():
        if canonical not in allowed:
            invalid_mappings.append((synonym, canonical))

    assert not invalid_mappings, (
        f"Synonyms map to invalid signals: {invalid_mappings}"
    )


def test_batch_summary_includes_taxonomy_metadata():
    """Test that batch_summary includes taxonomy_version and framework_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=1,
            output_root=tmpdir,
            mock_judge=True,
            target="scripted",
            debug=False,
        )

        meta = result["batch_meta"]
        assert "taxonomy_version" in meta, "batch_meta should include taxonomy_version"
        assert "framework_id" in meta, "batch_meta should include framework_id"
        assert "rubric_id" in meta, "batch_meta should include rubric_id"

        assert meta["taxonomy_version"] == get_taxonomy_version()
        assert meta["framework_id"] == "gdpr"
        assert meta["rubric_id"] == "gdpr_phase0_v1"


def test_mock_batch_has_high_signals_strict_accuracy():
    """Test that mock batch run achieves high signals_strict_accuracy with aligned taxonomy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=2,
            output_root=tmpdir,
            mock_judge=True,
            target="scripted",
            debug=False,
        )

        agg = result["aggregate_metrics"]

        # With mock judge returning expected outcomes and aligned taxonomy,
        # signals_strict_accuracy should be 1.0 (100%)
        assert "signals_strict_accuracy" in agg
        assert agg["signals_strict_accuracy"] >= 0.7, (
            f"Expected signals_strict_accuracy >= 0.7, got {agg['signals_strict_accuracy']}"
        )

        # Actually should be 1.0 since mock returns exact expected values
        assert agg["signals_strict_accuracy"] == 1.0, (
            f"Mock judge with aligned taxonomy should have 100% signals_strict_accuracy, "
            f"got {agg['signals_strict_accuracy']}"
        )
