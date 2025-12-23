"""Test batch runner functionality."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from aigov_eval.batch_runner import run_batch


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
