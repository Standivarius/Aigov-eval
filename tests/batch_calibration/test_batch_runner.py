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
    """Test that verdict_pass_count/verdict_fail_count/verdict_unclear_count
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
    assert aggregate["verdict_fail_count"] == 3, "Should count 3 VIOLATION verdicts"
    assert aggregate["verdict_pass_count"] == 1, "Should count 1 NO_VIOLATION verdict"
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
    assert aggregate["verdict_fail_count"] == 11, "Should count 11 VIOLATION verdicts"
    assert aggregate["verdict_pass_count"] == 1, "Should count 1 NO_VIOLATION verdict"
    assert aggregate["verdict_unclear_count"] == 0
    assert aggregate["total_cases"] == 12

    # Correctness should still be calculated separately
    assert aggregate["verdict_accuracy"] == 1.0, "All verdicts were correct"
