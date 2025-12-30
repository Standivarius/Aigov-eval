"""Tests for offline judge runner."""

import json
import tempfile
from pathlib import Path

from aigov_eval.offline_judge_runner import generate_judge_output, run_offline_judge


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
    assert output["verdict"] in ["VIOLATION", "NO_VIOLATION", "UNCLEAR"]

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
    """Test that offline judge runner processes all fixtures."""
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

        # Validate one output file schema
        sample_output = output_files[0]
        with open(sample_output, 'r') as f:
            data = json.load(f)

        assert "verdict" in data
        assert "signals" in data
        assert "citations" in data
        assert "rationale" in data
        assert "judge_meta" in data


def test_offline_judge_validates_signals():
    """Test that offline judge validates signals against taxonomy."""
    fixture_path = Path("cases/calibration/cal_001_lack_of_consent.json")

    output = generate_judge_output(fixture_path)

    # All signals should be valid (from taxonomy)
    valid_signals = {
        "lack_of_consent",
        "inadequate_transparency",
        "excessive_data_collection",
        "purpose_limitation_breach",
        "inadequate_security",
        "unlawful_processing",
        "rights_violation",
        "missing_dpia",
        "inadequate_dpo",
        "breach_notification_failure",
        "international_transfer_violation",
        "profiling_without_safeguards",
        "special_category_violation",
        "children_data_violation",
        "data_minimization_breach",
        "accuracy_violation",
        "retention_violation",
        "accountability_breach",
        "processor_contract_violation",
        "cross_border_cooperation_failure",
    }

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
