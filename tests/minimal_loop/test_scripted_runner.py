from pathlib import Path

from aigov_eval.runner import run_scenario


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "examples" / "scenarios"


def test_scripted_pii_run_fails(tmp_path):
    result = run_scenario(
        scenario_path=str(SCENARIOS / "pii_disclosure.yaml"),
        target_name="scripted",
        output_root=str(tmp_path),
        config={},
    )
    assert len(result.scores) == 1
    score = result.scores[0]
    assert score["category"] == "PII_DISCLOSURE"
    assert score["pass"] is False
    assert (result.run_dir / "transcript.json").exists()
    assert (result.run_dir / "scores.json").exists()
    assert (result.run_dir / "evidence_pack.json").exists()
    assert (result.run_dir / "run_meta.json").exists()


def test_scripted_special_category_run_fails(tmp_path):
    result = run_scenario(
        scenario_path=str(SCENARIOS / "special_category_leak.yaml"),
        target_name="scripted",
        output_root=str(tmp_path),
        config={},
    )
    assert len(result.scores) == 1
    score = result.scores[0]
    assert score["category"] == "SPECIAL_CATEGORY_LEAK"
    assert score["pass"] is False
    assert score["findings"], "Expected special-category findings"
    assert "health" in score["findings"][0]["detected_fields"]
    assert score["findings"][0]["turn_index"] == 5
    assert "Ion Popescu was diagnosed with type 2 diabetes" in score["findings"][0]["excerpt"]
