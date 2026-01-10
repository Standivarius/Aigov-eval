"""Optional EP bundle->execute smoke test."""

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


def _extract_line_value(output: str, prefix: str) -> str:
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    return ""


def test_ep_bundle_execute_smoke(tmp_path: Path) -> None:
    if not _env_truthy("AIGOV_RUN_EP_SMOKE"):
        pytest.skip("AIGOV_RUN_EP_SMOKE not set; skipping EP bundle smoke test.")

    if shutil.which("aigov-ep") is None:
        pytest.skip("Install EP: pushd ..\\AiGov-mvp; pip install -e .; popd")

    help_result = subprocess.run(
        ["aigov-ep", "execute", "--help"],
        capture_output=True,
        text=True,
    )
    if "--bundle-dir" not in help_result.stdout:
        pytest.fail("aigov-ep execute missing --bundle-dir; install EP from ..\\AiGov-mvp")

    bundles_out = tmp_path / "bundles"
    runs_out = tmp_path / "runs"
    scenario_path = Path(__file__).resolve().parents[2] / "examples" / "scenarios" / "pii_disclosure.yaml"

    bundle_result = subprocess.run(
        [
            "aigov-ep",
            "bundle",
            "--scenario",
            str(scenario_path),
            "--out",
            str(bundles_out),
        ],
        capture_output=True,
        text=True,
    )
    assert bundle_result.returncode == 0, (
        f"stdout:\n{bundle_result.stdout}\nstderr:\n{bundle_result.stderr}"
    )
    bundle_dir = _extract_line_value(bundle_result.stdout, "BUNDLE_DIR=")
    assert bundle_dir, f"BUNDLE_DIR not found in output:\n{bundle_result.stdout}"

    execute_result = subprocess.run(
        [
            "aigov-ep",
            "execute",
            "--bundle-dir",
            bundle_dir,
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
    run_dir_raw = _extract_line_value(execute_result.stdout, "RUN_DIR=")
    assert run_dir_raw, f"RUN_DIR not found in output:\n{execute_result.stdout}"

    run_dir = Path(run_dir_raw)
    if not run_dir.is_absolute():
        run_dir = (Path.cwd() / run_dir).resolve()

    required = ["scenario.json", "transcript.json", "run_meta.json"]
    missing = [name for name in required if not (run_dir / name).exists()]
    assert not missing, f"Missing Stage A artifacts in {run_dir}: {missing}"

    unexpected = ["scores.json", "evidence_pack.json"]
    present = [name for name in unexpected if (run_dir / name).exists()]
    assert not present, f"Unexpected Stage B artifacts in {run_dir}: {present}"

    judge_result = subprocess.run(
        ["aigov-ep", "judge", "--run-dir", str(run_dir)],
        capture_output=True,
        text=True,
    )
    assert judge_result.returncode == 0, (
        f"stdout:\n{judge_result.stdout}\nstderr:\n{judge_result.stderr}"
    )

    required_b = ["scores.json", "evidence_pack.json"]
    missing_b = [name for name in required_b if not (run_dir / name).exists()]
    assert not missing_b, f"Missing Stage B artifacts in {run_dir}: {missing_b}"
