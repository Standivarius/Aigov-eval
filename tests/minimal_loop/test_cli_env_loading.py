from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_cli_loads_dotenv_for_mock_llm(monkeypatch, tmp_path):
    pytest.importorskip("dotenv")
    env_path = tmp_path / ".env"
    env_path.write_text("OPENROUTER_API_KEY=devkey\n", encoding="utf-8")

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    import aigov_eval.env as env_module
    import aigov_eval.cli as cli_module

    importlib.reload(env_module)
    importlib.reload(cli_module)

    monkeypatch.setattr(env_module, "find_dotenv", lambda: str(env_path))

    class DummyResult:
        run_id = "test-run"
        run_dir = tmp_path / "runs" / "test-run"

    def fake_run_scenario(**_kwargs):
        return DummyResult()

    monkeypatch.setattr(cli_module, "run_scenario", fake_run_scenario)

    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "scenarios"
        / "pii_disclosure.yaml"
    )

    result = cli_module.main(
        [
            "run",
            "--scenario",
            str(scenario_path),
            "--target",
            "mock-llm",
            "--out",
            str(tmp_path / "runs"),
        ]
    )

    assert result == 0
