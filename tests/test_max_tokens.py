"""Tests for max_tokens default and enforcement."""

from __future__ import annotations

import argparse
from unittest.mock import Mock

import pytest

from aigov_eval.cli import main
from aigov_eval.targets.mock_llm import MockTargetAdapter


def test_cli_run_max_tokens_default():
    """Test that CLI run command defaults max_tokens to 500."""
    from aigov_eval.cli import main
    import argparse

    # Parse args to check default
    parser = argparse.ArgumentParser(prog="aigov_eval")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--scenario", required=True)
    run_parser.add_argument("--target", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--max-tokens", type=int, default=500)

    args = parser.parse_args(["run", "--scenario", "test.yaml", "--target", "scripted", "--out", "/tmp"])

    assert args.max_tokens == 500, "Default max_tokens should be 500"


def test_cli_batch_run_max_tokens_default():
    """Test that CLI batch-run command defaults max_tokens to 500."""
    import argparse

    parser = argparse.ArgumentParser(prog="aigov_eval")
    subparsers = parser.add_subparsers(dest="command")

    batch_parser = subparsers.add_parser("batch-run")
    batch_parser.add_argument("--cases-dir", required=True)
    batch_parser.add_argument("--out", required=True)
    batch_parser.add_argument("--max-tokens", type=int, default=500)

    args = parser.parse_args(["batch-run", "--cases-dir", "cases", "--out", "/tmp"])

    assert args.max_tokens == 500, "Default max_tokens should be 500"


def test_mock_llm_enforces_max_tokens_cap(monkeypatch):
    """Test that MockTargetAdapter enforces max_tokens <= 500."""
    # Mock environment and dependencies
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {"category": "TEST"}

    # Test with max_tokens > 500
    config_high = {"max_tokens": 1000}
    adapter = MockTargetAdapter(scenario, config_high)

    # Mock urllib to capture payload
    captured_payload = {}

    def mock_urlopen(req, timeout=None):
        import json
        nonlocal captured_payload
        captured_payload = json.loads(req.data.decode("utf-8"))

        # Return mock response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": "test response"}}],
            "usage": {}
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Call respond
    adapter._respond_llm([{"role": "user", "content": "test"}])

    # Verify max_tokens was capped at 500
    assert captured_payload["max_tokens"] == 500, "max_tokens should be capped at 500"

    # Test with max_tokens < 500
    config_low = {"max_tokens": 200}
    adapter2 = MockTargetAdapter(scenario, config_low)
    adapter2._respond_llm([{"role": "user", "content": "test"}])

    assert captured_payload["max_tokens"] == 200, "max_tokens should be 200 when below cap"

    # Test with no max_tokens specified
    config_none = {}
    adapter3 = MockTargetAdapter(scenario, config_none)
    adapter3._respond_llm([{"role": "user", "content": "test"}])

    assert captured_payload["max_tokens"] == 500, "max_tokens should default to 500"
