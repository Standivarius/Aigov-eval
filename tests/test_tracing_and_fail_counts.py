"""Tests for OpenRouter tracing and batch report fail counts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


def test_batch_report_fail_counts_match_recomputed(tmp_path):
    """Test that batch report fail counts match recomputed values from case_results."""
    from aigov_eval.batch_runner import _calculate_aggregate_metrics

    # Create mock case results with some failures
    case_results = [
        # Case 1: Both pass
        {
            "metrics": {
                "required_recall_pass": True,
                "allowed_only_pass": True,
                "verdict_repeatability": 1.0,
                "signals_repeatability": 1.0,
            }
        },
        # Case 2: Required recall fails
        {
            "metrics": {
                "required_recall_pass": False,
                "allowed_only_pass": True,
                "verdict_repeatability": 0.8,
                "signals_repeatability": 0.9,
            }
        },
        # Case 3: Allowed only fails
        {
            "metrics": {
                "required_recall_pass": True,
                "allowed_only_pass": False,
                "verdict_repeatability": 1.0,
                "signals_repeatability": 0.7,
            }
        },
        # Case 4: Both fail
        {
            "metrics": {
                "required_recall_pass": False,
                "allowed_only_pass": False,
                "verdict_repeatability": 0.6,
                "signals_repeatability": 0.5,
            }
        },
        # Case 5: Both pass
        {
            "metrics": {
                "required_recall_pass": True,
                "allowed_only_pass": True,
                "verdict_repeatability": 1.0,
                "signals_repeatability": 1.0,
                "modal_verdict": "VIOLATION",
                "modal_signals": [],
            }
        },
    ]

    aggregate = _calculate_aggregate_metrics(case_results)

    # Recompute fail counts manually
    required_recall_passes = [
        cr["metrics"]["required_recall_pass"]
        for cr in case_results
        if "required_recall_pass" in cr["metrics"]
    ]
    allowed_only_passes = [
        cr["metrics"]["allowed_only_pass"]
        for cr in case_results
        if "allowed_only_pass" in cr["metrics"]
    ]

    expected_required_fail_count = sum(1 for p in required_recall_passes if not p)
    expected_allowed_fail_count = sum(1 for p in allowed_only_passes if not p)

    # Verify accuracy calculations
    assert aggregate["required_recall_accuracy"] == sum(required_recall_passes) / len(required_recall_passes)
    assert aggregate["allowed_only_accuracy"] == sum(allowed_only_passes) / len(allowed_only_passes)

    # Verify fail counts
    assert aggregate["required_recall_case_fail_count"] == expected_required_fail_count
    assert aggregate["allowed_only_case_fail_count"] == expected_allowed_fail_count

    # Specific values for this test
    assert expected_required_fail_count == 2  # Cases 2 and 4
    assert expected_allowed_fail_count == 2  # Cases 3 and 4
    assert aggregate["required_recall_accuracy"] == 3/5  # 60%
    assert aggregate["allowed_only_accuracy"] == 3/5  # 60%


def test_openrouter_tracing_enabled(monkeypatch, capsys):
    """Test that OpenRouter tracing logs requests and responses when enabled."""
    from aigov_eval.targets.mock_llm import _trace_request, _trace_response

    # Enable tracing
    monkeypatch.setenv("AIGOV_TRACE_OPENROUTER", "1")

    # Test request tracing
    _trace_request("test_run:target:test_case:1", "gpt-4", 500, 1234)
    captured = capsys.readouterr()
    assert "[TRACE-REQ]" in captured.out
    assert "test_run:target:test_case:1" in captured.out
    assert "model=gpt-4" in captured.out
    assert "max_tokens=500" in captured.out
    assert "prompt_chars=1234" in captured.out

    # Test response tracing
    usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    _trace_response("test_run:target:test_case:1", usage, "openai/gpt-4")
    captured = capsys.readouterr()
    assert "[TRACE-RESP]" in captured.out
    assert "test_run:target:test_case:1" in captured.out
    assert "tokens=100/50/150" in captured.out
    assert "provider=openai/gpt-4" in captured.out


def test_openrouter_tracing_disabled_by_default(capsys):
    """Test that tracing is disabled by default (no env var)."""
    from aigov_eval.targets.mock_llm import _trace_request, _trace_response

    # Ensure env var is not set
    if "AIGOV_TRACE_OPENROUTER" in os.environ:
        del os.environ["AIGOV_TRACE_OPENROUTER"]

    _trace_request("test_run:target:test_case:1", "gpt-4", 500, 1234)
    _trace_response("test_run:target:test_case:1", {"total_tokens": 150})

    captured = capsys.readouterr()
    assert "[TRACE-REQ]" not in captured.out
    assert "[TRACE-RESP]" not in captured.out


def test_judge_applies_max_tokens_cap(monkeypatch):
    """Test that judge applies max_tokens <= 500 cap."""
    from aigov_eval.judge import _run_openrouter_judge, MAX_TOKENS_CAP

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    captured_request_body = {}

    def mock_urlopen(req, timeout=None):
        nonlocal captured_request_body
        captured_request_body = json.loads(req.data.decode("utf-8"))

        # Return mock response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"verdict": "NO_VIOLATION", "signals": [], "citations": [], "rationale": []}'}}],
            "usage": {"total_tokens": 100}
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    messages = [{"role": "user", "content": "test"}]
    meta = {"scenario_id": "test", "framework": "GDPR"}

    _run_openrouter_judge(messages, meta, {
        "model": "test-model",
        "temperature": 0.0,
        "top_p": 1.0,
        "base_url": "https://openrouter.ai/api/v1"
    })

    # Verify max_tokens was set to the cap
    assert "max_tokens" in captured_request_body
    assert captured_request_body["max_tokens"] == MAX_TOKENS_CAP
    assert captured_request_body["max_tokens"] == 500


def test_mock_llm_target_applies_max_tokens_cap(monkeypatch):
    """Test that mock-llm target applies max_tokens <= 500 cap."""
    from aigov_eval.targets.mock_llm import MockTargetAdapter, MAX_TOKENS_CAP

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {"category": "TEST", "scenario_id": "test"}
    config = {"max_tokens": 2000, "run_id": "test_run"}  # Try to set higher than cap

    adapter = MockTargetAdapter(scenario, config)

    captured_payload = {}

    def mock_urlopen(req, timeout=None):
        nonlocal captured_payload
        captured_payload = json.loads(req.data.decode("utf-8"))

        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Success"}}],
            "usage": {"total_tokens": 100}
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    adapter._respond_llm([{"role": "user", "content": "test"}])

    # Verify max_tokens was capped at 500
    assert captured_payload["max_tokens"] == MAX_TOKENS_CAP
    assert captured_payload["max_tokens"] == 500
