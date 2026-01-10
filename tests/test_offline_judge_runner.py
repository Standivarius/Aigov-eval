"""Tests for offline judge runner."""

import json
import tempfile
from pathlib import Path

from aigov_eval.offline_judge_runner import generate_judge_output, run_offline_judge
from aigov_eval.taxonomy import get_allowed_signal_ids, normalize_verdict


def test_generate_judge_output_schema():
    """Test that generated judge output matches expected schema."""
    # Use existing calibration case
    fixture_path = Path("cases/calibration/cal_001_lack_of_consent.json")

    output = generate_judge_output(fixture_path)

    # Validate required fields
    assert "verdict" in output
    assert "signals" in output
    assert "citations" in output
    assert "rationale" in output
    assert "judge_meta" in output

    # Validate verdict values
    canonical = {"INFRINGEMENT", "COMPLIANT", "UNDECIDED"}
    assert normalize_verdict(output["verdict"]) in canonical

    # Validate types
    assert isinstance(output["signals"], list)
    assert isinstance(output["citations"], list)
    assert isinstance(output["rationale"], list)
    assert isinstance(output["judge_meta"], dict)

    # Validate judge_meta fields
    meta = output["judge_meta"]
    assert "model" in meta
    assert "temperature" in meta
    assert "top_p" in meta
    assert "base_url" in meta
    assert "mock" in meta
    assert "timestamp_utc" in meta
    assert "source_fixture" in meta
    assert "scenario_id" in meta

    # Validate offline-specific metadata
    assert meta["model"] == "offline-judge-v1"
    assert meta["base_url"] == "offline"
    assert meta["mock"] is True
    assert meta["source_fixture"] == "cal_001_lack_of_consent.json"


def test_run_offline_judge():
    """Test that offline judge runner processes all fixtures and produces behaviour_json output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fixtures_dir = Path("cases/calibration")
        output_dir = Path(tmpdir) / "output"

        summary = run_offline_judge(
            fixtures_dir=fixtures_dir,
            output_dir=output_dir,
            verbose=False
        )

        # Validate summary
        assert summary["processed"] == 12  # 12 calibration cases
        assert summary["total_fixtures"] == 12
        assert summary["errors"] == []
        assert summary["output_dir"] == str(output_dir)

        # Validate output files exist
        output_files = list(output_dir.glob("*_judge_output.json"))
        assert len(output_files) == 12

        # Validate summary file exists
        assert (output_dir / "_summary.json").exists()

        # Validate one output file has behaviour_json schema (NOT internal schema)
        sample_output = output_files[0]
        with open(sample_output, 'r') as f:
            data = json.load(f)

        # Check for behaviour_json fields (after mapping)
        assert "audit_id" in data
        assert "run_id" in data
        assert "finding_id" in data
        assert "scenario_id" in data
        assert "framework" in data
        assert "rating" in data  # NOT "verdict"
        assert "reasoning" in data  # NOT "rationale"
        assert "legal_references" in data  # NOT "citations"
        assert "signals" in data
        assert "severity" in data
        assert "inspect_provenance" in data  # NOT "judge_meta"

        # Validate rating is mapped correctly
    canonical = {"INFRINGEMENT", "COMPLIANT", "UNDECIDED"}
    assert normalize_verdict(data["rating"]) in canonical


def test_offline_judge_validates_signals():
    """Test that offline judge validates signals against taxonomy."""
    fixture_path = Path("cases/calibration/cal_001_lack_of_consent.json")

    output = generate_judge_output(fixture_path)

    # All signals should be valid (from taxonomy)
    valid_signals = get_allowed_signal_ids()

    for signal in output["signals"]:
        assert signal in valid_signals, f"Signal '{signal}' not in taxonomy"


if __name__ == "__main__":
    # Run tests manually if pytest not available
    print("Running test_generate_judge_output_schema...")
    test_generate_judge_output_schema()
    print("✓ test_generate_judge_output_schema passed")

    print("Running test_run_offline_judge...")
    test_run_offline_judge()
    print("✓ test_run_offline_judge passed")

    print("Running test_offline_judge_validates_signals...")
    test_offline_judge_validates_signals()
    print("✓ test_offline_judge_validates_signals passed")

    print("\nAll tests passed!")
