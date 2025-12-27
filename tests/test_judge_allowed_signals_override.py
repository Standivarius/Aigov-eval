"""Tests for judge allowed_signals_override and unscored_findings."""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest


def test_judge_filters_signals_with_override(monkeypatch):
    """Test that allowed_signals_override filters out non-allowed signals."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_override",
        "framework": "GDPR",
        "run_id": "test_run"
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response with multiple signals
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "VIOLATION",
                        "signals": ["lack_of_consent", "inadequate_security"],
                        "citations": ["Art. 6"],
                        "rationale": "Multiple violations found."
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

    # Run judge with override that only allows "lack_of_consent"
    result = run_judge(
        messages,
        scenario,
        mock=False,
        allowed_signals_override={"lack_of_consent"}
    )

    # Verify only allowed signal is in output
    assert "lack_of_consent" in result["signals"]
    assert "inadequate_security" not in result["signals"]

    # Verify filtered signals appear in other_signals
    assert "other_signals" in result
    assert "inadequate_security" in result["other_signals"]


def test_judge_unscored_findings_preserved(monkeypatch):
    """Test that unscored_findings is preserved when provided."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_findings",
        "framework": "GDPR",
        "run_id": "test_run"
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response with unscored_findings
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "VIOLATION",
                        "signals": ["lack_of_consent"],
                        "citations": ["Art. 6"],
                        "rationale": "Violation found.",
                        "unscored_findings": ["Missing privacy policy", "No cookie banner"]
                    })
                }
            }],
            "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = run_judge(messages, scenario, mock=False)

    # Verify unscored_findings is preserved
    assert "unscored_findings" in result
    assert result["unscored_findings"] == ["Missing privacy policy", "No cookie banner"]


def test_judge_unscored_findings_defaults_to_empty(monkeypatch):
    """Test that unscored_findings defaults to [] when omitted."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_defaults",
        "framework": "GDPR",
        "run_id": "test_run"
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response WITHOUT unscored_findings
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "NO_VIOLATION",
                        "signals": [],
                        "citations": [],
                        "rationale": "No violations."
                    })
                }
            }],
            "usage": {"prompt_tokens": 50, "completion_tokens": 15, "total_tokens": 65},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = run_judge(messages, scenario, mock=False)

    # Verify unscored_findings defaults to []
    assert "unscored_findings" in result
    assert result["unscored_findings"] == []


def test_judge_unscored_findings_invalid_format_normalized(monkeypatch):
    """Test that invalid unscored_findings format is normalized to []."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_invalid",
        "framework": "GDPR",
        "run_id": "test_run"
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response with invalid unscored_findings (not a list)
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "verdict": "NO_VIOLATION",
                        "signals": [],
                        "citations": [],
                        "rationale": "No violations.",
                        "unscored_findings": "not a list"
                    })
                }
            }],
            "usage": {"prompt_tokens": 50, "completion_tokens": 15, "total_tokens": 65},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = run_judge(messages, scenario, mock=False)

    # Verify invalid format is normalized to []
    assert "unscored_findings" in result
    assert result["unscored_findings"] == []


def test_mock_judge_includes_unscored_findings():
    """Test that mock judge includes unscored_findings field."""
    from aigov_eval.judge import run_judge

    scenario = {
        "scenario_id": "test_mock",
        "framework": "GDPR",
        "expected_outcome": {
            "verdict": "VIOLATION",
            "required_signals": ["lack_of_consent"],
            "allowed_extra_signals": []
        }
    }

    messages = [{"role": "user", "content": "Test message"}]

    result = run_judge(messages, scenario, mock=True)

    # Verify mock judge includes unscored_findings
    assert "unscored_findings" in result
    assert result["unscored_findings"] == []


def test_gdpr_scorer_passes_scenario_signals_to_judge(monkeypatch):
    """Test that GDPR scorer passes scenario-scoped signals to judge."""
    from aigov_eval.scorers.gdpr_compliance import score_gdpr_compliance
    from aigov_eval.judge import run_judge

    # Track what allowed_signals_override was passed to run_judge
    captured_override = None

    def mock_run_judge(messages, meta, mock=False, allowed_signals_override=None):
        nonlocal captured_override
        captured_override = allowed_signals_override
        return {
            "verdict": "VIOLATION",
            "signals": ["lack_of_consent"],
            "citations": ["Art. 6"],
            "rationale": ["Test rationale"],
            "unscored_findings": [],
            "judge_meta": {"mock": mock}
        }

    monkeypatch.setattr("aigov_eval.scorers.gdpr_compliance.run_judge", mock_run_judge)

    # Test with v2 format scenario
    scenario = {
        "scenario_id": "test_scorer",
        "framework": "GDPR",
        "expected_outcome": {
            "verdict": "VIOLATION",
            "required_signals": ["lack_of_consent", "special_category_violation"],
            "allowed_extra_signals": ["purpose_limitation_breach"]
        }
    }

    transcript = [{"role": "user", "content": "Test"}]
    evidence = {}

    result = score_gdpr_compliance(transcript, scenario, evidence, mock_judge=False)

    # Verify the override set equals required ∪ allowed_extra
    assert captured_override is not None
    expected_set = {"lack_of_consent", "special_category_violation", "purpose_limitation_breach"}
    assert captured_override == expected_set

    # Verify result includes unscored_findings
    assert "unscored_findings" in result


def test_gdpr_scorer_handles_legacy_signals_format(monkeypatch):
    """Test that GDPR scorer handles legacy signals field."""
    from aigov_eval.scorers.gdpr_compliance import score_gdpr_compliance

    captured_override = None

    def mock_run_judge(messages, meta, mock=False, allowed_signals_override=None):
        nonlocal captured_override
        captured_override = allowed_signals_override
        return {
            "verdict": "VIOLATION",
            "signals": ["lack_of_consent"],
            "citations": ["Art. 6"],
            "rationale": ["Test rationale"],
            "unscored_findings": [],
            "judge_meta": {"mock": mock}
        }

    monkeypatch.setattr("aigov_eval.scorers.gdpr_compliance.run_judge", mock_run_judge)

    # Test with legacy format scenario
    scenario = {
        "scenario_id": "test_legacy",
        "framework": "GDPR",
        "expected_outcome": {
            "verdict": "VIOLATION",
            "signals": ["lack_of_consent", "inadequate_security"]
        }
    }

    transcript = [{"role": "user", "content": "Test"}]
    evidence = {}

    result = score_gdpr_compliance(transcript, scenario, evidence, mock_judge=False)

    # Verify the override set uses legacy signals
    assert captured_override == {"lack_of_consent", "inadequate_security"}


def test_gdpr_scorer_no_override_when_no_expected_outcome(monkeypatch):
    """Test that GDPR scorer passes None override when no expected_outcome."""
    from aigov_eval.scorers.gdpr_compliance import score_gdpr_compliance

    captured_override = None

    def mock_run_judge(messages, meta, mock=False, allowed_signals_override=None):
        nonlocal captured_override
        captured_override = allowed_signals_override
        return {
            "verdict": "UNCLEAR",
            "signals": [],
            "citations": [],
            "rationale": ["No expected outcome"],
            "unscored_findings": [],
            "judge_meta": {"mock": mock}
        }

    monkeypatch.setattr("aigov_eval.scorers.gdpr_compliance.run_judge", mock_run_judge)

    # Test with no expected_outcome
    scenario = {
        "scenario_id": "test_no_expected",
        "framework": "GDPR"
    }

    transcript = [{"role": "user", "content": "Test"}]
    evidence = {}

    result = score_gdpr_compliance(transcript, scenario, evidence, mock_judge=False)

    # Verify override is None (uses full taxonomy)
    assert captured_override is None
