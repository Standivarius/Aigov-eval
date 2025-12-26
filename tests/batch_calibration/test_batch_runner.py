"""Test batch runner functionality."""

import json
import os
import tempfile
from collections import Counter
from pathlib import Path

import pytest

from aigov_eval.batch_runner import run_batch, _calculate_aggregate_metrics


def test_batch_run_creates_outputs():
    """Test that batch-run creates expected outputs in mock mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run batch with mock judge (deterministic, no network)
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=2,  # Small number for testing
            output_root=tmpdir,
            mock_judge=True,
            target="scripted",
            debug=False,
        )

        # Verify batch_summary was created
        batch_dir = Path(tmpdir) / result["batch_meta"]["batch_id"]
        assert batch_dir.exists(), "Batch directory not created"

        summary_file = batch_dir / "batch_summary.json"
        assert summary_file.exists(), "batch_summary.json not created"

        report_file = batch_dir / "batch_report.md"
        assert report_file.exists(), "batch_report.md not created"

        # Verify summary structure
        with open(summary_file, "r") as f:
            summary = json.load(f)

        assert "batch_meta" in summary
        assert "aggregate_metrics" in summary
        assert "case_results" in summary

        # Verify aggregate metrics
        agg = summary["aggregate_metrics"]
        assert "total_cases" in agg
        assert agg["total_cases"] >= 12
        assert "mean_verdict_repeatability" in agg
        assert "mean_signals_repeatability" in agg

        # Verify case results
        assert len(summary["case_results"]) >= 12
        for case_result in summary["case_results"]:
            assert "scenario_id" in case_result
            assert "metrics" in case_result
            assert "runs" in case_result
            assert len(case_result["runs"]) == 2  # repeats=2


def test_batch_run_calculates_metrics():
    """Test that batch-run calculates repeatability and correctness metrics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=3,
            output_root=tmpdir,
            mock_judge=True,
            target="scripted",
            debug=False,
        )

        # In mock mode, we should have perfect repeatability
        # (since mock judge returns expected_outcome deterministically)
        agg = result["aggregate_metrics"]

        # With mock judge, verdict repeatability should be 1.0 (100%)
        assert agg["mean_verdict_repeatability"] == 1.0, \
            f"Expected perfect repeatability in mock mode, got {agg['mean_verdict_repeatability']}"

        # Check correctness metrics exist
        assert "verdict_accuracy" in agg
        assert agg["verdict_accuracy"] == 1.0, "Mock judge should have 100% accuracy"


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set, skipping live judge test"
)
def test_batch_run_with_live_judge():
    """Test batch-run with live OpenRouter judge (requires API key)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run with just 1 case and 1 repeat to minimize API cost
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=1,
            output_root=tmpdir,
            mock_judge=False,  # Use live judge
            target="scripted",
            debug=False,
        )

        assert "batch_meta" in result
        assert result["batch_meta"]["mock_judge"] is False


def test_verdict_counts_match_modal_verdict_distribution():
<<<<<<< HEAD
    """Test that verdict_no_violation_count/verdict_violation_count/verdict_unclear_count
=======
    """Test that verdict_pass_count/verdict_fail_count/verdict_unclear_count
>>>>>>> origin/main
    are computed from modal_verdict values, not from correctness."""
    # Create mock case results with known modal verdicts
    case_results = [
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0}},
        {"metrics": {"modal_verdict": "NO_VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0}},
        {"metrics": {"modal_verdict": "UNCLEAR", "verdict_repeatability": 1.0, "signals_repeatability": 1.0}},
        {"metrics": {"modal_verdict": "UNCLEAR", "verdict_repeatability": 1.0, "signals_repeatability": 1.0}},
    ]

    aggregate = _calculate_aggregate_metrics(case_results)

    # Verify counts match the actual modal verdict distribution
<<<<<<< HEAD
    assert aggregate["verdict_violation_count"] == 3, "Should count 3 VIOLATION verdicts"
    assert aggregate["verdict_no_violation_count"] == 1, "Should count 1 NO_VIOLATION verdict"
=======
    assert aggregate["verdict_fail_count"] == 3, "Should count 3 VIOLATION verdicts"
    assert aggregate["verdict_pass_count"] == 1, "Should count 1 NO_VIOLATION verdict"
>>>>>>> origin/main
    assert aggregate["verdict_unclear_count"] == 2, "Should count 2 UNCLEAR verdicts"
    assert aggregate["total_cases"] == 6


def test_verdict_counts_independent_of_correctness():
    """Test that verdict counts are not affected by verdict_correctness values."""
    # Create case results where correctness differs from verdict distribution
    # 11 VIOLATION (all correct), 1 NO_VIOLATION (correct)
    case_results = [
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
        {"metrics": {"modal_verdict": "NO_VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "verdict_correctness": True}},
    ]

    aggregate = _calculate_aggregate_metrics(case_results)

    # Bug scenario from issue: should be 11 VIOLATION, 1 NO_VIOLATION
    # NOT 12 pass, 0 fail (which was the bug - counting correctness instead)
<<<<<<< HEAD
    assert aggregate["verdict_violation_count"] == 11, "Should count 11 VIOLATION verdicts"
    assert aggregate["verdict_no_violation_count"] == 1, "Should count 1 NO_VIOLATION verdict"
=======
    assert aggregate["verdict_fail_count"] == 11, "Should count 11 VIOLATION verdicts"
    assert aggregate["verdict_pass_count"] == 1, "Should count 1 NO_VIOLATION verdict"
>>>>>>> origin/main
    assert aggregate["verdict_unclear_count"] == 0
    assert aggregate["total_cases"] == 12

    # Correctness should still be calculated separately
    assert aggregate["verdict_accuracy"] == 1.0, "All verdicts were correct"
<<<<<<< HEAD


def test_case_results_contain_observability_fields():
    """Test that case_results contain expected observability fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=1,
            output_root=tmpdir,
            mock_judge=True,
            target="scripted",
            debug=False,
        )

        # Check that all case results have the observability fields
        for case_result in result["case_results"]:
            assert "expected_required_signals" in case_result, \
                f"Missing expected_required_signals in {case_result['scenario_id']}"
            assert "expected_allowed_extra_signals" in case_result, \
                f"Missing expected_allowed_extra_signals in {case_result['scenario_id']}"
            assert "missing_required_signals" in case_result, \
                f"Missing missing_required_signals in {case_result['scenario_id']}"
            assert "extra_unallowed_signals" in case_result, \
                f"Missing extra_unallowed_signals in {case_result['scenario_id']}"

            # Verify they are lists
            assert isinstance(case_result["expected_required_signals"], list)
            assert isinstance(case_result["expected_allowed_extra_signals"], list)
            assert isinstance(case_result["missing_required_signals"], list)
            assert isinstance(case_result["extra_unallowed_signals"], list)


def test_aggregate_metrics_contain_recall_counts():
    """Test that aggregate_metrics contain required_recall counts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=1,
            output_root=tmpdir,
            mock_judge=True,
            target="scripted",
            debug=False,
        )

        agg = result["aggregate_metrics"]

        # Verify count fields exist
        assert "required_recall_missing_count" in agg
        assert "required_recall_case_fail_count" in agg
        assert "allowed_only_case_fail_count" in agg

        # In mock mode, signals should match expected, so counts should be 0
        assert agg["required_recall_missing_count"] == 0, \
            "Mock judge should have no missing required signals"
        assert agg["required_recall_case_fail_count"] == 0, \
            "Mock judge should have no cases with missing required signals"
        assert agg["allowed_only_case_fail_count"] == 0, \
            "Mock judge should have no cases with extra unallowed signals"


def test_cal_001_observability_fields_correct():
    """Test cal_001 has correct observability fields with v2 format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=1,
            output_root=tmpdir,
            mock_judge=True,
            target="scripted",
            debug=False,
        )

        # Find cal_001 case result
        cal_001 = None
        for cr in result["case_results"]:
            if cr["scenario_id"] == "cal_001_lack_of_consent":
                cal_001 = cr
                break

        assert cal_001 is not None, "cal_001_lack_of_consent not found in results"

        # Verify v2 fields are populated correctly
        assert cal_001["expected_required_signals"] == ["lack_of_consent"], \
            f"Expected required_signals to be ['lack_of_consent'], got {cal_001['expected_required_signals']}"
        assert set(cal_001["expected_allowed_extra_signals"]) == {"inadequate_transparency", "purpose_limitation_breach"}, \
            f"Unexpected allowed_extra_signals: {cal_001['expected_allowed_extra_signals']}"

        # In mock mode, modal signals should match expected exactly, so no missing/extra
        assert cal_001["missing_required_signals"] == [], \
            f"Mock mode should have no missing required, got {cal_001['missing_required_signals']}"
        assert cal_001["extra_unallowed_signals"] == [], \
            f"Mock mode should have no extra unallowed, got {cal_001['extra_unallowed_signals']}"


def test_cal_002_observability_fields_correct():
    """Test cal_002 has correct observability fields with v2 format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_batch(
            cases_dir="cases/calibration",
            repeats=1,
            output_root=tmpdir,
            mock_judge=True,
            target="scripted",
            debug=False,
        )

        # Find cal_002 case result
        cal_002 = None
        for cr in result["case_results"]:
            if cr["scenario_id"] == "cal_002_special_category_data":
                cal_002 = cr
                break

        assert cal_002 is not None, "cal_002_special_category_data not found in results"

        # Verify v2 fields are populated correctly
        assert set(cal_002["expected_required_signals"]) == {"special_category_violation", "lack_of_consent"}, \
            f"Unexpected required_signals: {cal_002['expected_required_signals']}"
        assert cal_002["expected_allowed_extra_signals"] == ["purpose_limitation_breach"], \
            f"Unexpected allowed_extra_signals: {cal_002['expected_allowed_extra_signals']}"

        # Check metrics include required_recall and allowed_only
        assert "required_recall" in cal_002["metrics"], "Missing required_recall metric"
        assert "allowed_only" in cal_002["metrics"], "Missing allowed_only metric"
        assert cal_002["metrics"]["required_recall"] is True, "Mock mode should have perfect required_recall"
        assert cal_002["metrics"]["allowed_only"] is True, "Mock mode should have perfect allowed_only"


def test_aggregate_required_recall_accuracy():
    """Test that aggregate required_recall_accuracy is computed correctly."""
    # Create mock case results with mixed required_recall outcomes
    case_results = [
        {
            "metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "required_recall": True, "allowed_only": True},
            "missing_required_signals": [],
            "extra_unallowed_signals": [],
        },
        {
            "metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "required_recall": False, "allowed_only": True},
            "missing_required_signals": ["lack_of_consent"],
            "extra_unallowed_signals": [],
        },
        {
            "metrics": {"modal_verdict": "VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "required_recall": True, "allowed_only": False},
            "missing_required_signals": [],
            "extra_unallowed_signals": ["made_up_signal", "another_signal"],
        },
        {
            "metrics": {"modal_verdict": "NO_VIOLATION", "verdict_repeatability": 1.0, "signals_repeatability": 1.0, "required_recall": False, "allowed_only": True},
            "missing_required_signals": ["special_category_violation"],
            "extra_unallowed_signals": [],
        },
    ]

    aggregate = _calculate_aggregate_metrics(case_results)

    # 2 out of 4 have required_recall=True
    assert aggregate["required_recall_accuracy"] == 0.5, \
        f"Expected required_recall_accuracy=0.5, got {aggregate['required_recall_accuracy']}"

    # 3 out of 4 have allowed_only=True
    assert aggregate["allowed_only_accuracy"] == 0.75, \
        f"Expected allowed_only_accuracy=0.75, got {aggregate['allowed_only_accuracy']}"

    # Count missing signals: 1 + 1 = 2
    assert aggregate["required_recall_missing_count"] == 2, \
        f"Expected required_recall_missing_count=2, got {aggregate['required_recall_missing_count']}"

    # Cases with missing required: 2 (case 2 and 4)
    assert aggregate["required_recall_case_fail_count"] == 2, \
        f"Expected required_recall_case_fail_count=2, got {aggregate['required_recall_case_fail_count']}"

    # Cases with extra unallowed: 1 (case 3)
    assert aggregate["allowed_only_case_fail_count"] == 1, \
        f"Expected allowed_only_case_fail_count=1, got {aggregate['allowed_only_case_fail_count']}"
=======
>>>>>>> origin/main
