"""Tests for robust judge JSON parsing and trace persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


def test_parse_judge_json_clean():
    """Test parsing clean JSON (fast path)."""
    from aigov_eval.judge import parse_judge_json

    content = '{"verdict": "VIOLATION", "signals": ["lack_of_consent"], "citations": [], "rationale": "Test"}'
    result = parse_judge_json(content)

    assert result["verdict"] == "VIOLATION"
    assert result["signals"] == ["lack_of_consent"]


def test_parse_judge_json_with_markdown_fences():
    """Test parsing JSON wrapped in markdown code fences."""
    from aigov_eval.judge import parse_judge_json

    content = '''```json
{
  "verdict": "VIOLATION",
  "signals": ["special_category_violation"],
  "citations": ["Art. 9"],
  "rationale": "Health data processed."
}
```'''

    result = parse_judge_json(content)

    assert result["verdict"] == "VIOLATION"
    assert result["signals"] == ["special_category_violation"]
    assert result["citations"] == ["Art. 9"]


def test_parse_judge_json_with_plain_fences():
    """Test parsing JSON wrapped in plain markdown fences."""
    from aigov_eval.judge import parse_judge_json

    content = '''```
{"verdict": "NO_VIOLATION", "signals": [], "citations": [], "rationale": "Compliant"}
```'''

    result = parse_judge_json(content)

    assert result["verdict"] == "NO_VIOLATION"
    assert result["signals"] == []


def test_parse_judge_json_with_leading_text():
    """Test parsing JSON with leading explanatory text."""
    from aigov_eval.judge import parse_judge_json

    content = '''Here is my analysis:

{"verdict": "UNCLEAR", "signals": [], "citations": [], "rationale": "Insufficient info"}'''

    result = parse_judge_json(content)

    assert result["verdict"] == "UNCLEAR"


def test_parse_judge_json_with_trailing_text():
    """Test parsing JSON with trailing text."""
    from aigov_eval.judge import parse_judge_json

    content = '''{"verdict": "VIOLATION", "signals": ["lack_of_consent"], "citations": [], "rationale": "No consent"}

This concludes my analysis.'''

    result = parse_judge_json(content)

    assert result["verdict"] == "VIOLATION"
    assert result["signals"] == ["lack_of_consent"]


def test_parse_judge_json_empty_content():
    """Test that empty content raises JSONDecodeError."""
    from aigov_eval.judge import parse_judge_json

    with pytest.raises(json.JSONDecodeError, match="Empty content"):
        parse_judge_json("")


def test_parse_judge_json_no_valid_json():
    """Test that content without JSON raises JSONDecodeError."""
    from aigov_eval.judge import parse_judge_json

    with pytest.raises(json.JSONDecodeError, match="No valid JSON found"):
        parse_judge_json("This is just plain text without any JSON")


def test_parse_judge_json_preserves_unscored_findings():
    """Test that unscored_findings field is preserved during parsing."""
    from aigov_eval.judge import parse_judge_json

    content = '''{
  "verdict": "VIOLATION",
  "signals": ["lack_of_consent"],
  "citations": ["Art. 6"],
  "rationale": "Missing consent",
  "unscored_findings": ["No privacy policy", "Missing cookie banner"]
}'''

    result = parse_judge_json(content)

    assert "unscored_findings" in result
    assert result["unscored_findings"] == ["No privacy policy", "Missing cookie banner"]


def test_judge_with_markdown_fenced_response(monkeypatch, tmp_path):
    """Test full judge flow with markdown-fenced response."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_fenced",
        "framework": "GDPR",
        "run_id": "test_run",
        "run_dir": str(tmp_path)
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response with markdown-fenced JSON
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": '''```json
{
  "verdict": "VIOLATION",
  "signals": ["lack_of_consent"],
  "citations": ["Art. 6"],
  "rationale": "No consent obtained"
}
```'''
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

    # Verify parsing worked despite markdown fences
    assert result["verdict"] == "VIOLATION"
    assert "lack_of_consent" in result["signals"]
    assert result["citations"] == ["Art. 6"]


def test_judge_with_leading_text_response(monkeypatch, tmp_path):
    """Test full judge flow with leading text before JSON."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_leading",
        "framework": "GDPR",
        "run_id": "test_run",
        "run_dir": str(tmp_path)
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response with leading text
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": '''Let me analyze this case:

{"verdict": "NO_VIOLATION", "signals": [], "citations": [], "rationale": "All requirements met"}'''
                }
            }],
            "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = run_judge(messages, scenario, mock=False)

    # Verify parsing worked despite leading text
    assert result["verdict"] == "NO_VIOLATION"
    assert result["signals"] == []


def test_judge_parse_failure_includes_excerpt(monkeypatch, tmp_path):
    """Test that parse failure includes raw content excerpt in error."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_error",
        "framework": "GDPR",
        "run_id": "test_run",
        "run_dir": str(tmp_path)
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response with invalid JSON
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": "This is not valid JSON at all, just plain text"
                }
            }],
            "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = run_judge(messages, scenario, mock=False)

    # Verify it returns UNCLEAR with error details
    assert result["verdict"] == "UNCLEAR"
    assert "error" in result["judge_meta"]
    assert "error_raw_excerpt" in result["judge_meta"]
    assert "This is not valid JSON" in result["judge_meta"]["error_raw_excerpt"]


def test_trace_persistence_when_enabled(monkeypatch, tmp_path):
    """Test that trace files are persisted when AIGOV_TRACE_OPENROUTER=1."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("AIGOV_TRACE_OPENROUTER", "1")

    scenario = {
        "scenario_id": "test_trace",
        "framework": "GDPR",
        "run_id": "test_run_trace",
        "run_dir": str(tmp_path)
    }

    messages = [{"role": "user", "content": "Test trace message"}]

    # Mock OpenRouter response
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": '{"verdict": "NO_VIOLATION", "signals": [], "citations": [], "rationale": "OK"}'
                }
            }],
            "usage": {"prompt_tokens": 40, "completion_tokens": 15, "total_tokens": 55},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = run_judge(messages, scenario, mock=False)

    # Verify trace files were created
    assert (tmp_path / "openrouter_judge_request.json").exists()
    assert (tmp_path / "openrouter_judge_response.json").exists()
    assert (tmp_path / "openrouter_judge_content.txt").exists()

    # Verify content
    with open(tmp_path / "openrouter_judge_content.txt") as f:
        content = f.read()
        assert "NO_VIOLATION" in content


def test_trace_not_persisted_when_disabled(monkeypatch, tmp_path):
    """Test that trace files are NOT persisted when AIGOV_TRACE_OPENROUTER!=1."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    # Explicitly unset trace env var
    monkeypatch.delenv("AIGOV_TRACE_OPENROUTER", raising=False)

    scenario = {
        "scenario_id": "test_no_trace",
        "framework": "GDPR",
        "run_id": "test_run_no_trace",
        "run_dir": str(tmp_path)
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock OpenRouter response
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": '{"verdict": "NO_VIOLATION", "signals": [], "citations": [], "rationale": "OK"}'
                }
            }],
            "usage": {"prompt_tokens": 40, "completion_tokens": 15, "total_tokens": 55},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = run_judge(messages, scenario, mock=False)

    # Verify trace files were NOT created
    assert not (tmp_path / "openrouter_judge_request.json").exists()
    assert not (tmp_path / "openrouter_judge_response.json").exists()
    assert not (tmp_path / "openrouter_judge_content.txt").exists()


def test_judge_preserves_unscored_findings_with_fences(monkeypatch, tmp_path):
    """Test that unscored_findings survives fence stripping."""
    from aigov_eval.judge import run_judge

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    scenario = {
        "scenario_id": "test_findings_fence",
        "framework": "GDPR",
        "run_id": "test_run",
        "run_dir": str(tmp_path)
    }

    messages = [{"role": "user", "content": "Test message"}]

    # Mock response with both signals and unscored_findings in fenced JSON
    def mock_urlopen(req, timeout=None):
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": '''```json
{
  "verdict": "VIOLATION",
  "signals": ["lack_of_consent"],
  "citations": ["Art. 6"],
  "rationale": "Missing consent",
  "unscored_findings": ["No DPO contact", "Privacy policy outdated"]
}
```'''
                }
            }],
            "usage": {"prompt_tokens": 60, "completion_tokens": 40, "total_tokens": 100},
            "model": "google/gemini-2.0-flash-001"
        }).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        return mock_response

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    result = run_judge(messages, scenario, mock=False)

    # Verify both signals and unscored_findings are present
    assert result["verdict"] == "VIOLATION"
    assert "lack_of_consent" in result["signals"]
    assert result["unscored_findings"] == ["No DPO contact", "Privacy policy outdated"]
