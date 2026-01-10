"""Optional EP CLI smoke test."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


_TRUTHY = {"1", "true", "yes"}


def _env_truthy(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() in _TRUTHY


def _extract_run_dir(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("RUN_DIR="):
            return line.split("=", 1)[1].strip()
    return ""


def test_ep_cli_execute_smoke(tmp_path: Path) -> None:
    if not _env_truthy("AIGOV_RUN_EP_SMOKE"):
        pytest.skip("AIGOV_RUN_EP_SMOKE not set; skipping EP CLI smoke test.")

    if shutil.which("aigov-ep") is None:
        pytest.skip(
            "aigov-ep not found on PATH. Install with: pushd ..\\AiGov-mvp; pip install -e .; popd"
        )

    scenario_path = Path(__file__).resolve().parents[2] / "examples" / "scenarios" / "pii_disclosure.yaml"
    out_dir = tmp_path / "runs"

    result = subprocess.run(
        [
            "aigov-ep",
            "execute",
            "--scenario",
            str(scenario_path),
            "--target",
            "scripted",
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    run_dir_raw = _extract_run_dir(result.stdout)
    assert run_dir_raw, f"RUN_DIR not found in output:\n{result.stdout}"

    run_dir = Path(run_dir_raw)
    if not run_dir.is_absolute():
        run_dir = (Path.cwd() / run_dir).resolve()

    assert run_dir.exists(), f"RUN_DIR does not exist: {run_dir}"

    required = ["transcript.json", "scores.json", "run_meta.json", "evidence_pack.json"]
    missing = [name for name in required if not (run_dir / name).exists()]
    assert not missing, f"Missing artifacts in {run_dir}: {missing}"
