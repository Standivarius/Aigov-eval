import json
import pathlib
import subprocess
import sys


def _latest_batch_dir(out_dir: pathlib.Path) -> pathlib.Path:
    batches = sorted(out_dir.glob("batch_*"))
    assert batches, f"No batch_* folders found under {out_dir}"
    return batches[-1]


def test_batch_run_mock_smoke(tmp_path):
    out_dir = tmp_path / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "aigov_eval.cli",
        "batch-run",
        "--cases-dir",
        "cases/calibration",
        "--repeats",
        "1",
        "--out",
        str(out_dir),
        "--mock-judge",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"batch-run failed\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"

    latest = _latest_batch_dir(out_dir)
    summary_path = latest / "batch_summary.json"
    assert summary_path.exists(), f"Missing {summary_path}"

    d = json.loads(summary_path.read_text())
    agg = d["aggregate_metrics"]

    assert agg.get("total_cases") == 12
    assert agg.get("required_recall_accuracy") == 1.0
    assert agg.get("allowed_only_accuracy") == 1.0

    # tolerate either naming scheme
    v_violation = agg.get("verdict_violation_count", agg.get("verdict_fail_count"))
    v_no_violation = agg.get("verdict_no_violation_count", agg.get("verdict_pass_count"))
    v_unclear = agg.get("verdict_unclear_count", 0)

    assert v_violation == 11
    assert v_no_violation == 1
    assert v_unclear == 0
