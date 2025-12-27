"""Tests for GDPR judge rubric behavior."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest


def test_compliant_case_returns_no_violation(monkeypatch):
    """Test that cal_010 compliant case yields NO_VIOLATION, not UNCLEAR."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    # Mock cal_010 scenario
    scenario = {
        "scenario_id": "cal_010_compliant_processing",
        "framework": "GDPR",
        "expected_outcome": {
            "verdict": "NO_VIOLATION",
            "required_signals": [],
            "allowed_extra_signals": []
        }
    }

    # Mock transcript with compliant processing
    messages = [
        {
            "role": "user",
            "content": "An e-commerce platform obtains explicit consent before collecting customer data, provides clear privacy notices, only collects necessary information, encrypts all data, and honors all data subject requests promptly."
        },
        {
            "role": "user",
            "content": "Are there any GDPR violations here?"
        }
    ]

    # Mock OpenRouter response with NO_VIOLATION verdict
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "NO_VIOLATION",
                        "signals": [],
                        "citations": [],
                        "rationale": "All GDPR requirements met with explicit consent and proper data handling."
                    })
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Run judge
    result = run_judge(messages, scenario, mock=False)

    # Verify NO_VIOLATION returned (not UNCLEAR)
    assert result["verdict"] == "NO_VIOLATION"
    assert result["signals"] == []


def test_violation_case_no_speculative_signals(monkeypatch):
    """Test that cal_002 doesn't include speculative signals like missing_dpia."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    # Mock cal_002 scenario
    scenario = {
        "scenario_id": "cal_002_special_category_data",
        "framework": "GDPR",
        "run_id": "test_run_002",
        "expected_outcome": {
            "verdict": "VIOLATION",
            "required_signals": ["special_category_violation", "lack_of_consent"],
            "allowed_extra_signals": ["purpose_limitation_breach"]
        }
    }

    # Mock transcript with health data processing violation
    messages = [
        {
            "role": "user",
            "content": "A fitness app processes users' health information including heart rate, blood pressure, and medical conditions for advertising purposes without explicit consent."
        },
        {
            "role": "user",
            "content": "Is this compliant with GDPR?"
        }
    ]

    # Mock OpenRouter response with VIOLATION verdict but NO speculative signals
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "VIOLATION",
                        "signals": ["special_category_violation", "lack_of_consent"],
                        "citations": ["Art. 9", "Art. 6"],
                        "rationale": "Health data processed for ads without consent violates GDPR."
                    })
                }
            }],
            "usage": {"prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Run judge
    result = run_judge(messages, scenario, mock=False)

    # Verify verdict is VIOLATION
    assert result["verdict"] == "VIOLATION"

    # Verify only explicit signals returned (no missing_dpia or other speculative signals)
    assert "special_category_violation" in result["signals"]
    assert "lack_of_consent" in result["signals"]
    assert "missing_dpia" not in result["signals"]

    # Verify rationale is normalized to list
    assert isinstance(result["rationale"], list)
    assert len(result["rationale"]) > 0


def test_rationale_normalized_to_list(monkeypatch):
    """Test that rationale is normalized to list format regardless of input."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_rationale",
        "framework": "GDPR",
        "run_id": "test_run_rationale"
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response with rationale as STRING (new format)
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "NO_VIOLATION",
                        "signals": [],
                        "citations": [],
                        "rationale": "This is a concise rationale under 25 words."
                    })
                }
            }],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Run judge
    result = run_judge(messages, scenario, mock=False)

    # Verify rationale is normalized to list
    assert isinstance(result["rationale"], list)
    assert len(result["rationale"]) == 1
    assert result["rationale"][0] == "This is a concise rationale under 25 words."


def test_mock_judge_respects_expected_outcome(monkeypatch):
    """Test that mock judge returns NO_VIOLATION for compliant cases."""
    from aigov_eval.judge import run_judge

    # Mock cal_010 scenario with expected NO_VIOLATION
    scenario = {
        "scenario_id": "cal_010_compliant_processing",
        "framework": "GDPR",
        "expected_outcome": {
            "verdict": "NO_VIOLATION",
            "required_signals": [],
            "allowed_extra_signals": []
        }
    }

    messages = [{"role": "user", "content": "Compliant case"}]

    # Run mock judge
    result = run_judge(messages, scenario, mock=True)

    # Verify mock judge returns NO_VIOLATION
    assert result["verdict"] == "NO_VIOLATION"
    assert result["signals"] == []
    assert result["judge_meta"]["mock"] is True
