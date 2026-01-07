import os
import json
import glob
from pathlib import Path

import pytest

from aigov_eval.cli import main


@pytest.mark.skipif("OPENROUTER_API_KEY" not in os.environ, reason="no API key")
def test_live_judge_smoke(tmp_path: Path):
    # Run live batch (fast, repeats=1)
    args = [
        "batch-run",
        "--cases-dir", "cases/calibration",
        "--repeats", "1",
        "--out", str(tmp_path),
        "--target", "mock-llm",
    ]
    main(args)

    # batch-run writes: <out>/batch_<timestamp>/batch_summary.json
    batches = sorted(glob.glob(str(tmp_path / "batch_*")))
    assert batches, f"No batch_* dir created under: {tmp_path}"
    latest = Path(batches[-1])

    summary_file = latest / "batch_summary.json"
    assert summary_file.exists(), f"Missing: {summary_file}"

    meta = json.loads(summary_file.read_text()).get("batch_meta", {})
    assert meta.get("target") == "mock-llm"
    assert meta.get("mock_judge") is False
