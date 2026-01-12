"""Optional EP CLI judge smoke test."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


_TRUTHY = {"1", "true", "yes"}


def _env_truthy(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() in _TRUTHY


def _extract_line_value(output: str, prefix: str) -> str:
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    return ""


def _load_canonical_verdicts() -> set[str]:
    contracts_path = Path(__file__).resolve().parents[2] / "aigov_eval" / "taxonomy" / "contracts" / "verdicts.json"
    payload = json.loads(contracts_path.read_text(encoding="utf-8"))
    return set(payload.get("canonical") or [])


def _collect_verdicts(obj: object, found: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "verdict" and isinstance(value, str):
                found.append(value)
            else:
                _collect_verdicts(value, found)
        return
    if isinstance(obj, list):
        for item in obj:
            _collect_verdicts(item, found)


def test_ep_cli_judge_smoke(tmp_path: Path) -> None:
    if not _env_truthy("AIGOV_RUN_EP_SMOKE"):
        pytest.skip("AIGOV_RUN_EP_SMOKE not set; skipping EP judge smoke test.")

    if shutil.which("aigov-ep") is None:
        pytest.skip(
            "aigov-ep not found on PATH. Install with: pushd ..\\AiGov-mvp; pip install -e .; popd"
        )

    scenario_path = Path(__file__).resolve().parents[2] / "examples" / "scenarios" / "pii_disclosure.yaml"
    runs_out = tmp_path / "runs"

    execute_result = subprocess.run(
        [
            "aigov-ep",
            "execute",
            "--scenario",
            str(scenario_path),
            "--target",
            "scripted",
            "--out",
            str(runs_out),
        ],
        capture_output=True,
        text=True,
    )
    assert execute_result.returncode == 0, (
        f"stdout:\n{execute_result.stdout}\nstderr:\n{execute_result.stderr}"
    )
    run_dir = _extract_line_value(execute_result.stdout, "RUN_DIR=")
    assert run_dir, f"RUN_DIR not found in output:\n{execute_result.stdout}"

    judge_result = subprocess.run(
        ["aigov-ep", "judge", "--run-dir", run_dir],
        capture_output=True,
        text=True,
    )
    assert judge_result.returncode == 0, (
        f"stdout:\n{judge_result.stdout}\nstderr:\n{judge_result.stderr}"
    )

    judge_dir = _extract_line_value(judge_result.stdout, "JUDGE_DIR=") or run_dir
    run_path = Path(judge_dir)
    if not run_path.is_absolute():
        run_path = (Path.cwd() / run_path).resolve()

    required = ["scores.json", "evidence_pack.json"]
    missing = [name for name in required if not (run_path / name).exists()]
    assert not missing, f"Missing Stage B artifacts in {run_path}: {missing}"

    scores = json.loads((run_path / "scores.json").read_text(encoding="utf-8"))
    canonical = _load_canonical_verdicts()
    verdicts: list[str] = []
    _collect_verdicts(scores, verdicts)
    assert all(verdict in canonical for verdict in verdicts), (
        f"Non-canonical verdicts in scores.json: {verdicts}"
    )
