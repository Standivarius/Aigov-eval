"""Tests for timeout handling and retry logic."""

from __future__ import annotations

import socket
import urllib.error
from unittest.mock import Mock, patch

import pytest


def test_batch_runner_continues_on_timeout(tmp_path, monkeypatch):
    """Test that batch-run doesn't crash when target adapter raises timeout."""
    from aigov_eval.batch_runner import _run_case_with_repeats
    from pathlib import Path

    # Mock scenario
    case_file = Path("cases/calibration/cal_001_lack_of_consent.json")
    batch_dir = tmp_path / "batch_test"
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Mock run_scenario to raise timeout on first call, succeed on second
    call_count = [0]

    def mock_run_scenario(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise socket.timeout("Connection timed out")

        # Return mock result for second call
        mock_result = Mock()
        mock_result.run_id = "test_run_002"
        mock_result.run_dir = tmp_path / "run_002"
        mock_result.scores = [
            {
                "scorer": "gdpr_compliance",
                "verdict": "VIOLATION",
                "signals": ["lack_of_consent"],
            }
        ]
        return mock_result

    # Mock load_scenario
    def mock_load_scenario(path):
        return {
            "scenario_id": "cal_001_test",
            "category": "GDPR_COMPLIANCE",
            "expected_outcome": {
                "verdict": "VIOLATION",
                "required_signals": ["lack_of_consent"],
            },
        }

    import aigov_eval.batch_runner as batch_module

    monkeypatch.setattr(batch_module, "run_scenario", mock_run_scenario)
    monkeypatch.setattr(batch_module, "load_scenario", mock_load_scenario)

    # Run with 2 repeats
    result = _run_case_with_repeats(
        case_file=case_file,
        repeats=2,
        batch_dir=batch_dir,
        mock_judge=True,
        target="scripted",
        debug=False,
        max_tokens=500,
    )

    # Verify batch didn't crash
    assert result is not None
    assert result["scenario_id"] == "cal_001_test"
    assert len(result["runs"]) == 2

    # First run should be marked as UNCLEAR with error
    assert result["runs"][0]["verdict"] == "UNCLEAR"
    assert result["runs"][0]["signals"] == []
    assert "error" in result["runs"][0]
    assert result["runs"][0]["error"]["error_type"] == "timeout"

    # Second run should succeed
    assert result["runs"][1]["verdict"] == "VIOLATION"
    assert result["runs"][1]["signals"] == ["lack_of_consent"]
    assert "error" not in result["runs"][1]

    # Metrics should include error count
    assert result["metrics"]["error_count"] == 1


def test_mock_llm_retry_logic(monkeypatch):
    """Test that MockTargetAdapter retries on transient failures."""
    from aigov_eval.targets.mock_llm import MockTargetAdapter
    import urllib.request
    import json

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {"category": "TEST"}
    config = {"max_tokens": 500}
    adapter = MockTargetAdapter(scenario, config)

    # Track attempts
    attempts = [0]

    def mock_urlopen(req, timeout=None):
        attempts[0] += 1

        # Fail first two attempts with 429, succeed on third
        if attempts[0] <= 2:
            error = urllib.error.HTTPError(
                req.full_url, 429, "Rate limit exceeded", {}, None
            )
            raise error

        # Success on third attempt
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {
                "choices": [{"message": {"content": "Success"}}],
                "usage": {"total_tokens": 100},
            }
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Patch time.sleep to avoid actual delays in tests
    monkeypatch.setattr("time.sleep", lambda x: None)

    # Call should succeed after retries
    response = adapter._respond_llm([{"role": "user", "content": "test"}])

    assert response["content"] == "Success"
    assert attempts[0] == 3  # Should have tried 3 times


def test_mock_llm_retry_exhaustion(monkeypatch):
    """Test that MockTargetAdapter raises error after max retries."""
    from aigov_eval.targets.mock_llm import MockTargetAdapter
    import urllib.request

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {"category": "TEST"}
    config = {"max_tokens": 500}
    adapter = MockTargetAdapter(scenario, config)

    def mock_urlopen(req, timeout=None):
        # Always fail with timeout
        raise socket.timeout("Connection timed out")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    monkeypatch.setattr("time.sleep", lambda x: None)

    # Should raise RuntimeError after exhausting retries
    with pytest.raises(RuntimeError, match="timed out"):
        adapter._respond_llm([{"role": "user", "content": "test"}])


def test_mock_llm_max_tokens_cap_preserved(monkeypatch):
    """Test that max_tokens cap at 500 is preserved even with retries."""
    from aigov_eval.targets.mock_llm import MockTargetAdapter
    import urllib.request
    import json

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {"category": "TEST"}
    config = {"max_tokens": 2000}  # Try to set higher than cap
    adapter = MockTargetAdapter(scenario, config)

    captured_payload = {}

    def mock_urlopen(req, timeout=None):
        nonlocal captured_payload
        captured_payload = json.loads(req.data.decode("utf-8"))

        mock_response = Mock()
        mock_response.read.return_value = json.dumps(
            {
                "choices": [{"message": {"content": "Success"}}],
                "usage": {"total_tokens": 100},
            }
        ).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    adapter._respond_llm([{"role": "user", "content": "test"}])

    # Verify max_tokens was capped at 500
    assert captured_payload["max_tokens"] == 500
