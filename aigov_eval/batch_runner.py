"""Batch runner for calibration tests."""

from __future__ import annotations

import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .loader import load_scenario
from .runner import run_scenario


def run_batch(
    cases_dir: str,
    repeats: int,
    output_root: str,
    mock_judge: bool = False,
    target: str = "scripted",
    debug: bool = False,
) -> dict:
    """
    Run batch calibration test.

    Args:
        cases_dir: Directory containing case JSON files
        repeats: Number of times to run each case
        output_root: Output directory root
        mock_judge: Use mock judge mode
        target: Target name (default: scripted)
        debug: Enable debug mode

    Returns:
        Batch summary dict
    """
    cases_path = Path(cases_dir)
    if not cases_path.exists():
        raise ValueError(f"Cases directory not found: {cases_dir}")

    # Find all case JSON files
    case_files = sorted(cases_path.glob("*.json"))
    if not case_files:
        raise ValueError(f"No JSON files found in {cases_dir}")

    # Create batch output directory
    output_path = Path(output_root)
    output_path.mkdir(parents=True, exist_ok=True)

    batch_id = _build_batch_id()
    batch_dir = output_path / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Collect git metadata
    git_sha = _get_git_sha()
    python_version = _get_python_version()

    batch_meta = {
        "batch_id": batch_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cases_dir": str(cases_dir),
        "repeats": repeats,
        "mock_judge": mock_judge,
        "target": target,
        "git_sha": git_sha,
        "python_version": python_version,
        "total_cases": len(case_files),
    }

    # Run all cases
    case_results = []
    for case_file in case_files:
        print(f"\nRunning case: {case_file.name} ({repeats} repeats)")
        case_result = _run_case_with_repeats(
            case_file=case_file,
            repeats=repeats,
            batch_dir=batch_dir,
            mock_judge=mock_judge,
            target=target,
            debug=debug,
        )
        case_results.append(case_result)
        print(f"  Verdict repeatability: {case_result['metrics']['verdict_repeatability']:.2%}")
        print(f"  Verdict correctness: {case_result['metrics'].get('verdict_correctness', 'N/A')}")

    # Calculate aggregate metrics
    aggregate_metrics = _calculate_aggregate_metrics(case_results)

    # Build batch summary
    batch_summary = {
        "batch_meta": batch_meta,
        "aggregate_metrics": aggregate_metrics,
        "case_results": case_results,
    }

    # Write outputs
    summary_path = batch_dir / "batch_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(batch_summary, f, indent=2, sort_keys=True)

    report_path = batch_dir / "batch_report.md"
    _write_batch_report(report_path, batch_summary)

    print(f"\n✓ Batch {batch_id} complete")
    print(f"  Outputs: {batch_dir}")
    print(f"  Summary: {summary_path}")
    print(f"  Report: {report_path}")

    return batch_summary


def _run_case_with_repeats(
    case_file: Path,
    repeats: int,
    batch_dir: Path,
    mock_judge: bool,
    target: str,
    debug: bool,
) -> dict:
    """Run a single case multiple times and calculate metrics."""
    scenario = load_scenario(str(case_file))
    scenario_id = scenario.get("scenario_id", case_file.stem)

    # Create case output directory
    case_dir = batch_dir / scenario_id
    case_dir.mkdir(parents=True, exist_ok=True)

    # Run repeats
    run_results = []
    for i in range(repeats):
        run_output = case_dir / f"run_{i+1:03d}"
        run_output.mkdir(parents=True, exist_ok=True)

        config = {
            "mock_judge": mock_judge,
        }

        result = run_scenario(
            scenario_path=str(case_file),
            target_name=target,
            output_root=str(run_output.parent),
            config=config,
        )

        # Extract GDPR compliance score if available
        gdpr_score = None
        for score in result.scores:
            if score.get("scorer") == "gdpr_compliance":
                gdpr_score = score
                break

        run_results.append({
            "run_id": result.run_id,
            "run_dir": str(result.run_dir),
            "verdict": gdpr_score.get("verdict") if gdpr_score else None,
            "signals": gdpr_score.get("signals", []) if gdpr_score else [],
        })

    # Calculate metrics
    metrics = _calculate_case_metrics(run_results, scenario)

    return {
        "scenario_id": scenario_id,
        "case_file": str(case_file),
        "repeats": repeats,
        "runs": run_results,
        "metrics": metrics,
    }


def _calculate_case_metrics(run_results: list[dict], scenario: dict) -> dict:
    """Calculate repeatability and correctness metrics for a case."""
    # Extract verdicts and signals
    verdicts = [r["verdict"] for r in run_results if r["verdict"]]
    signals_sets = [tuple(sorted(r["signals"])) for r in run_results]

    # Calculate modes
    verdict_counter = Counter(verdicts)
    signals_counter = Counter(signals_sets)

    modal_verdict = verdict_counter.most_common(1)[0][0] if verdict_counter else None
    modal_signals = list(signals_counter.most_common(1)[0][0]) if signals_counter else []

    # Repeatability = mode frequency / total runs
    verdict_repeatability = (
        verdict_counter.most_common(1)[0][1] / len(run_results)
        if verdict_counter else 0.0
    )
    signals_repeatability = (
        signals_counter.most_common(1)[0][1] / len(run_results)
        if signals_counter else 0.0
    )

    metrics = {
        "modal_verdict": modal_verdict,
        "modal_signals": modal_signals,
        "verdict_repeatability": verdict_repeatability,
        "signals_repeatability": signals_repeatability,
    }

    # Correctness (if expected_outcome exists)
    expected = scenario.get("expected_outcome", {})
    if expected:
        expected_verdict = expected.get("verdict")
        expected_signals = set(expected.get("signals", []))

        if expected_verdict and modal_verdict:
            metrics["verdict_correctness"] = modal_verdict == expected_verdict

        if expected_signals:
            modal_signals_set = set(modal_signals)
            metrics["signals_correctness_strict"] = modal_signals_set == expected_signals
            metrics["signals_correctness_subset"] = expected_signals.issubset(modal_signals_set)

    return metrics


def _calculate_aggregate_metrics(case_results: list[dict]) -> dict:
    """Calculate aggregate metrics across all cases."""
    total_cases = len(case_results)

    # Collect repeatability scores
    verdict_repeatability = [
        cr["metrics"]["verdict_repeatability"]
        for cr in case_results
    ]
    signals_repeatability = [
        cr["metrics"]["signals_repeatability"]
        for cr in case_results
    ]

    # Collect correctness (where available)
    verdict_correctness = [
        cr["metrics"].get("verdict_correctness")
        for cr in case_results
        if "verdict_correctness" in cr["metrics"]
    ]
    signals_strict = [
        cr["metrics"].get("signals_correctness_strict")
        for cr in case_results
        if "signals_correctness_strict" in cr["metrics"]
    ]
    signals_subset = [
        cr["metrics"].get("signals_correctness_subset")
        for cr in case_results
        if "signals_correctness_subset" in cr["metrics"]
    ]

    # Count modal verdicts across all cases
    modal_verdicts = [
        cr["metrics"].get("modal_verdict")
        for cr in case_results
    ]
    modal_verdict_counter = Counter(modal_verdicts)

    aggregate = {
        "total_cases": total_cases,
        "mean_verdict_repeatability": sum(verdict_repeatability) / total_cases if verdict_repeatability else 0.0,
        "mean_signals_repeatability": sum(signals_repeatability) / total_cases if signals_repeatability else 0.0,
        # Verdict distribution based on modal_verdict values
        "verdict_pass_count": modal_verdict_counter.get("NO_VIOLATION", 0),
        "verdict_fail_count": modal_verdict_counter.get("VIOLATION", 0),
        "verdict_unclear_count": modal_verdict_counter.get("UNCLEAR", 0),
    }

    if verdict_correctness:
        aggregate["verdict_accuracy"] = sum(verdict_correctness) / len(verdict_correctness)

    if signals_strict:
        aggregate["signals_strict_accuracy"] = sum(signals_strict) / len(signals_strict)

    if signals_subset:
        aggregate["signals_subset_accuracy"] = sum(signals_subset) / len(signals_subset)

    return aggregate


def _write_batch_report(path: Path, summary: dict) -> None:
    """Write batch report in Markdown format."""
    meta = summary["batch_meta"]
    agg = summary["aggregate_metrics"]
    cases = summary["case_results"]

    lines = [
        f"# Batch Calibration Report: {meta['batch_id']}",
        "",
        f"**Timestamp**: {meta['timestamp_utc']}  ",
        f"**Cases Directory**: {meta['cases_dir']}  ",
        f"**Repeats**: {meta['repeats']}  ",
        f"**Mock Judge**: {meta['mock_judge']}  ",
        f"**Target**: {meta['target']}  ",
        f"**Git SHA**: {meta['git_sha']}  ",
        f"**Python**: {meta['python_version']}  ",
        "",
        "---",
        "",
        "## Aggregate Metrics",
        "",
        f"- **Total Cases**: {agg['total_cases']}",
        f"- **Mean Verdict Repeatability**: {agg['mean_verdict_repeatability']:.2%}",
        f"- **Mean Signals Repeatability**: {agg['mean_signals_repeatability']:.2%}",
    ]

    # Verdict distribution from modal verdicts
    lines.extend([
        f"- **Verdict Pass Count (NO_VIOLATION)**: {agg['verdict_pass_count']}",
        f"- **Verdict Fail Count (VIOLATION)**: {agg['verdict_fail_count']}",
        f"- **Verdict Unclear Count**: {agg['verdict_unclear_count']}",
    ])

    if "verdict_accuracy" in agg:
        lines.append(f"- **Verdict Accuracy**: {agg['verdict_accuracy']:.2%}")

    if "signals_strict_accuracy" in agg:
        lines.append(f"- **Signals Strict Accuracy**: {agg['signals_strict_accuracy']:.2%}")

    if "signals_subset_accuracy" in agg:
        lines.append(f"- **Signals Subset Accuracy**: {agg['signals_subset_accuracy']:.2%}")

    lines.extend([
        "",
        "---",
        "",
        "## Case Results",
        "",
    ])

    for case in cases:
        m = case["metrics"]
        lines.extend([
            f"### {case['scenario_id']}",
            "",
            f"- **Repeats**: {case['repeats']}",
            f"- **Modal Verdict**: {m['modal_verdict']}",
            f"- **Modal Signals**: {', '.join(m['modal_signals']) if m['modal_signals'] else 'none'}",
            f"- **Verdict Repeatability**: {m['verdict_repeatability']:.2%}",
            f"- **Signals Repeatability**: {m['signals_repeatability']:.2%}",
        ])

        if "verdict_correctness" in m:
            lines.append(f"- **Verdict Correctness**: {'✓ PASS' if m['verdict_correctness'] else '✗ FAIL'}")

        if "signals_correctness_strict" in m:
            lines.append(f"- **Signals Strict**: {'✓ PASS' if m['signals_correctness_strict'] else '✗ FAIL'}")

        if "signals_correctness_subset" in m:
            lines.append(f"- **Signals Subset**: {'✓ PASS' if m['signals_correctness_subset'] else '✗ FAIL'}")

        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _build_batch_id() -> str:
    """Build batch ID with timestamp."""
    return f"batch_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _get_git_sha() -> str:
    """Get current git SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _get_python_version() -> str:
    """Get Python version."""
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
