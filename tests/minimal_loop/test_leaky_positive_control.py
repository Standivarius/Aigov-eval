from __future__ import annotations

import json
from pathlib import Path

from aigov_eval.runner import run_scenario
from aigov_eval.targets.mock_llm import MockTargetAdapter


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "examples" / "scenarios"


def test_non_leaky_mock_llm_passes(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_llm(self, _messages):
        return {"content": "I cannot share that information."}

    monkeypatch.setattr(MockTargetAdapter, "_respond_llm", fake_llm)

    result = run_scenario(
        scenario_path=str(SCENARIOS / "pii_disclosure_positive_control.yaml"),
        target_name="mock-llm",
        output_root=str(tmp_path),
        config={"leaky": False, "leak_profile": "pii_basic", "leak_after": 2},
    )

    score = next(s for s in result.scores if s["category"] == "PII_DISCLOSURE")
    assert score["pass"] is True
    assert score["findings"] == []


def test_leaky_mock_llm_fails_with_audit(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    result = run_scenario(
        scenario_path=str(SCENARIOS / "pii_disclosure_positive_control.yaml"),
        target_name="mock-llm",
        output_root=str(tmp_path),
        config={"leaky": True, "leak_profile": "pii_basic", "leak_after": 2},
    )

    score = next(s for s in result.scores if s["category"] == "PII_DISCLOSURE")
    assert score["pass"] is False
    assert score["findings"], "Expected PII findings in leaky mode"
    assert "email" in score["findings"][0]["detected_fields"]
    assert score["findings"][0]["turn_index"] == 3
    assert score["findings"][0]["excerpt"]

    evidence_path = result.run_dir / "evidence_pack.json"
    with open(evidence_path, "r", encoding="utf-8") as handle:
        evidence = json.load(handle)

    mock_audit = evidence.get("mock_audit")
    assert mock_audit == {"leaked_fields": ["email"], "turn_index": 3}
