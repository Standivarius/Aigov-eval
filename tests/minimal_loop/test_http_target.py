from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

from aigov_eval.runner import run_scenario
from aigov_eval.targets.http_target import HttpTargetAdapter


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "examples" / "scenarios"


class DummyResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def getcode(self) -> int:
        return 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _stub_http(
    monkeypatch,
    reply: str,
    audit: dict,
    expected_mode: str,
    expected_profile: str,
    expected_lengths: list[int],
    response_key: str = "reply",
):
    call_index = {"value": 0}

    def fake_urlopen(req, timeout=60):
        data = json.loads(req.data.decode("utf-8"))
        assert "message" not in data
        assert "messages" in data
        assert isinstance(data["messages"], list)
        idx = call_index["value"]
        assert len(data["messages"]) == expected_lengths[idx]
        for message in data["messages"]:
            assert "role" in message
            assert "content" in message
        call_index["value"] += 1

        assert data["leak_mode"] == expected_mode
        assert data["leak_profile"] == expected_profile
        assert data["session_id"] == "test-session"
        assert data["use_llm"] is False
        return DummyResponse({response_key: reply, "server_audit": audit})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


def _read_evidence(run_dir: Path) -> dict:
    with open(run_dir / "evidence_pack.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_http_pii_strict_passes(monkeypatch, tmp_path):
    _stub_http(
        monkeypatch,
        reply="I cannot share personal data.",
        audit={"leaked_fields": []},
        expected_mode="strict",
        expected_profile="pii",
        expected_lengths=[2, 4, 6],
    )
    result = run_scenario(
        scenario_path=str(SCENARIOS / "pii_disclosure_positive_control.yaml"),
        target_name="http",
        output_root=str(tmp_path),
        config={
            "base_url": "http://localhost:8000",
            "leak_mode": "strict",
            "leak_profile": "pii_basic",
            "use_llm": False,
            "session_id": "test-session",
        },
    )

    assert len(result.scores) == 1
    score = result.scores[0]
    assert score["category"] == "PII_DISCLOSURE"
    assert score["pass"] is True

    evidence = _read_evidence(result.run_dir)
    http_audit = evidence["http_audit"]
    http_raw = evidence["http_raw_response"]
    assert len(http_audit) == 3
    assert all(entry["leaked_fields"] == [] for entry in http_audit)
    assert len(http_raw) == 3
    assert "reply" in http_raw[0]


def test_http_pii_leaky_fails(monkeypatch, tmp_path):
    _stub_http(
        monkeypatch,
        reply="Ion Popescu's email is ion.popescu@example.com.",
        audit={"leaked_fields": ["email"]},
        expected_mode="leaky",
        expected_profile="pii",
        expected_lengths=[2, 4, 6],
    )
    result = run_scenario(
        scenario_path=str(SCENARIOS / "pii_disclosure_positive_control.yaml"),
        target_name="http",
        output_root=str(tmp_path),
        config={
            "base_url": "http://localhost:8000",
            "leak_mode": "leaky",
            "leak_profile": "pii_basic",
            "use_llm": False,
            "session_id": "test-session",
        },
    )

    assert len(result.scores) == 1
    score = result.scores[0]
    assert score["category"] == "PII_DISCLOSURE"
    assert score["pass"] is False
    assert score["findings"]
    assert "email" in score["findings"][0]["detected_fields"]

    evidence = _read_evidence(result.run_dir)
    http_audit = evidence["http_audit"]
    http_raw = evidence["http_raw_response"]
    assert len(http_audit) == 3
    assert http_audit[0]["leaked_fields"] == ["email"]
    assert len(http_raw) == 3


def test_http_special_strict_passes(monkeypatch, tmp_path):
    _stub_http(
        monkeypatch,
        reply="I cannot share medical information.",
        audit={"leaked_fields": []},
        expected_mode="strict",
        expected_profile="special_category",
        expected_lengths=[2, 4, 6],
    )
    result = run_scenario(
        scenario_path=str(SCENARIOS / "special_category_leak_positive_control.yaml"),
        target_name="http",
        output_root=str(tmp_path),
        config={
            "base_url": "http://localhost:8000",
            "leak_mode": "strict",
            "leak_profile": "special_category_basic",
            "use_llm": False,
            "session_id": "test-session",
        },
    )

    assert len(result.scores) == 1
    score = result.scores[0]
    assert score["category"] == "SPECIAL_CATEGORY_LEAK"
    assert score["pass"] is True

    evidence = _read_evidence(result.run_dir)
    http_audit = evidence["http_audit"]
    http_raw = evidence["http_raw_response"]
    assert len(http_audit) == 3
    assert all(entry["leaked_fields"] == [] for entry in http_audit)
    assert len(http_raw) == 3


def test_http_special_leaky_fails(monkeypatch, tmp_path):
    _stub_http(
        monkeypatch,
        reply="Ion Popescu was diagnosed with type 2 diabetes.",
        audit={"leaked_fields": ["health"]},
        expected_mode="leaky",
        expected_profile="special_category",
        expected_lengths=[2, 4, 6],
    )
    result = run_scenario(
        scenario_path=str(SCENARIOS / "special_category_leak_positive_control.yaml"),
        target_name="http",
        output_root=str(tmp_path),
        config={
            "base_url": "http://localhost:8000",
            "leak_mode": "leaky",
            "leak_profile": "special_category_basic",
            "use_llm": False,
            "session_id": "test-session",
        },
    )

    assert len(result.scores) == 1
    score = result.scores[0]
    assert score["category"] == "SPECIAL_CATEGORY_LEAK"
    assert score["pass"] is False
    assert score["findings"]
    assert "health" in score["findings"][0]["detected_fields"]

    evidence = _read_evidence(result.run_dir)
    http_audit = evidence["http_audit"]
    http_raw = evidence["http_raw_response"]
    assert len(http_audit) == 3
    assert http_audit[0]["leaked_fields"] == ["health"]
    assert len(http_raw) == 3


def test_http_response_empty_reply_raises(monkeypatch):
    def fake_urlopen(_req, _timeout=60, **_kwargs):
        return DummyResponse({"reply": "   ", "server_audit": {}})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    target = HttpTargetAdapter(
        scenario={},
        config={"base_url": "http://localhost:8000", "session_id": "test-session"},
    )
    with pytest.raises(RuntimeError) as excinfo:
        target.respond([{"role": "user", "content": "hello"}])
    assert "missing assistant text" in str(excinfo.value)


def test_http_response_alt_key(monkeypatch):
    _stub_http(
        monkeypatch,
        reply="hello",
        audit={},
        expected_mode="strict",
        expected_profile="pii",
        expected_lengths=[1],
        response_key="assistant_message",
    )
    target = HttpTargetAdapter(
        scenario={},
        config={
            "base_url": "http://localhost:8000",
            "session_id": "test-session",
            "leak_mode": "strict",
            "leak_profile": "pii_basic",
            "use_llm": False,
        },
    )
    response = target.respond([{"role": "user", "content": "hello"}])
    assert response["content"] == "hello"


def test_http_unknown_role_maps_to_user(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=60):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return DummyResponse({"reply": "ok", "server_audit": {}})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    target = HttpTargetAdapter(
        scenario={},
        config={
            "base_url": "http://localhost:8000",
            "session_id": "test-session",
            "leak_mode": "strict",
            "leak_profile": "pii_basic",
            "use_llm": False,
        },
    )
    target.respond(
        [
            {"role": "human", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "bot", "content": "assistant reply"},
        ]
    )
    roles = [msg["role"] for msg in captured["payload"]["messages"]]
    assert roles == ["user", "assistant", "assistant"]
