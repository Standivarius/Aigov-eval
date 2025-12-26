"""Test calibration cases exist and have required fields."""

import json
from pathlib import Path

import pytest


def test_calibration_cases_exist():
    """Verify calibration directory exists and contains JSON files."""
    cases_dir = Path("cases/calibration")
    assert cases_dir.exists(), "cases/calibration directory not found"

    case_files = list(cases_dir.glob("*.json"))
    assert len(case_files) >= 12, f"Expected at least 12 calibration cases, found {len(case_files)}"


def test_calibration_cases_have_required_fields():
    """Verify all calibration cases have required expected_outcome fields."""
    cases_dir = Path("cases/calibration")
    case_files = sorted(cases_dir.glob("*.json"))

    for case_file in case_files:
        with open(case_file, "r", encoding="utf-8") as f:
            case = json.load(f)

        # Check required fields
        assert "scenario_id" in case, f"{case_file.name}: missing scenario_id"
        assert "category" in case, f"{case_file.name}: missing category"
        assert case["category"] == "GDPR_COMPLIANCE", f"{case_file.name}: category must be GDPR_COMPLIANCE"
        assert "expected_outcome" in case, f"{case_file.name}: missing expected_outcome"

        expected = case["expected_outcome"]
        assert "verdict" in expected, f"{case_file.name}: missing expected_outcome.verdict"
        # V2 format: required_signals + allowed_extra_signals
        assert "required_signals" in expected, f"{case_file.name}: missing expected_outcome.required_signals"
        assert "allowed_extra_signals" in expected, f"{case_file.name}: missing expected_outcome.allowed_extra_signals"

        # Verify verdict is valid
        assert expected["verdict"] in ["VIOLATION", "NO_VIOLATION", "UNCLEAR"], \
            f"{case_file.name}: invalid verdict {expected['verdict']}"
