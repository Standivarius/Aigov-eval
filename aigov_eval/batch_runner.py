"""Batch runner for calibration tests.

Key points:
- Backwards-compatible CLI/API surface:
  * cli.py may call run_batch(output_root=...)
  * older code may call batch_run(..., output_root=...)
- Scenario-scoped scoring:
  * in-scope = required_signals ∪ allowed_extra_signals
  * out-of-scope extras are recorded as unscored_signals / extra_unallowed_signals (legacy)
- Timeout handling:
  * errors are normalised (socket.timeout => error_type="timeout")
  * metrics include error_count (required by tests)
"""

from __future__ import annotations

import json
import socket
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .loader import load_scenario
from .runner import run_scenario
from .taxonomy import get_taxonomy_version


def run_batch(
    cases_dir: str,
    repeats: int,
    out: str | None = None,
    *,
    output_root: str | None = None,
    mock_judge: bool = False,
    target: str = "scripted",
    debug: bool = False,
    max_tokens: int = 500,
) -> dict:
    """
    Run batch calibration test.

    Args:
        cases_dir: Directory containing case JSON files
        repeats: Number of times to run each case
        out: Output directory root (preferred param name)
        output_root: Output directory root (legacy/CLI compatibility)
        mock_judge: Use mock judge mode
        target: Target name (default: scripted)
        debug: Enable debug mode
        max_tokens: Max tokens for LLM responses

    Returns:
        Batch summary dict
    """
    out_dir = out or output_root
    if not out_dir:
        raise TypeError("run_batch() requires 'out' or 'output_root'")

    cases_path = Path(cases_dir)
    if not cases_path.exists():
        raise FileNotFoundError(f"Cases directory not found: {cases_dir}")

    # Create batch output directory
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_id = f"batch_{timestamp}"
    batch_dir = Path(out_dir) / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Repro metadata
    git_sha = _get_git_sha()
    python_version = _get_python_version()

    case_files = sorted(cases_path.glob("*.json"))
    case_results: list[dict[str, Any]] = []

    for case_file in case_files:
        print(f"\nRunning case: {case_file.name} ({repeats} repeats)")
        try:
            case_result = _run_case_with_repeats(
                case_file=case_file,
                repeats=repeats,
                batch_dir=batch_dir,
                mock_judge=mock_judge,
                target=target,
                debug=debug,
                max_tokens=max_tokens,
            )
            case_results.append(case_result)

            m = case_result["metrics"]
            print(f"  Verdict repeatability: {m['verdict_repeatability']:.2%}")
            if "verdict_correctness" in m:
                print(f"  Verdict correctness: {m['verdict_correctness']}")

        except Exception as e:
            print(f"Error running case {case_file.name}: {e}")
            if debug:
                raise
            # Keep batch moving, but record a minimal failed case so totals remain stable.
            case_results.append(
                {
                    "scenario_id": case_file.stem,
                    "case_file": str(case_file),
                    "repeats": repeats,
                    "runs": [],
                    "metrics": {
                        "modal_verdict": "UNCLEAR",
                        "modal_signals": [],
                        "verdict_repeatability": 0.0,
                        "signals_repeatability": 0.0,
                        "error_count": repeats,
                    },
                    "expected_required_signals": [],
                    "expected_allowed_extra_signals": [],
                    "score_set_signals": [],
                    "scored_actual_signals": [],
                    "unscored_signals": [],
                    "unscored_findings": [],
                    "missing_required_signals": [],
                    "extra_unallowed_signals": [],
                }
            )

    aggregate_metrics = _calculate_aggregate_metrics(case_results)

    batch_summary = {
        "batch_meta": {
            "batch_id": batch_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "cases_dir": cases_dir,
            "repeats": repeats,
            "mock_judge": mock_judge,
            "target": target,
            "git_sha": git_sha,
            "python_version": python_version,
            "framework_id": "gdpr",
            "taxonomy_version": get_taxonomy_version(),
            "rubric_id": "gdpr_phase0_v1",
            "total_cases": len(case_results),
            "max_tokens": max_tokens,
        },
        "aggregate_metrics": aggregate_metrics,
        "case_results": case_results,
    }

    summary_path = batch_dir / "batch_summary.json"
    summary_path.write_text(json.dumps(batch_summary, indent=2, sort_keys=True), encoding="utf-8")

    report_path = batch_dir / "batch_report.md"
    _write_batch_report(report_path, batch_summary)

    print(f"\n✓ Batch {batch_id} complete")
    print(f"  Outputs: {batch_dir}")
    print(f"  Summary: {summary_path}")
    print(f"  Report: {report_path}")

    return batch_summary


# Backwards-compatible alias (some older code may call batch_run)
def batch_run(
    cases_dir: str,
    repeats: int,
    output_root: str,
    mock_judge: bool = False,
    target: str = "scripted",
    debug: bool = False,
    max_tokens: int = 500,
) -> dict:
    return run_batch(
        cases_dir=cases_dir,
        repeats=repeats,
        output_root=output_root,
        mock_judge=mock_judge,
        target=target,
        debug=debug,
        max_tokens=max_tokens,
    )


def _classify_error(exc: Exception) -> dict[str, str]:
    """Normalise error types for reporting/tests."""
    msg = str(exc) or exc.__class__.__name__
    msg_l = msg.lower()

    # Map common timeout shapes to "timeout"
    if isinstance(exc, socket.timeout) or "timeout" in msg_l or "timed out" in msg_l:
        return {"error_type": "timeout", "error_msg": msg}

    # Rate limit / server error (useful for OpenRouter)
    if "rate limit" in msg_l or "429" in msg_l:
        return {"error_type": "rate_limit", "error_msg": msg}
    if any(code in msg_l for code in ("500", "502", "503", "504")):
        return {"error_type": "server_error", "error_msg": msg}

    # Default: class name (stable-ish)
    return {"error_type": exc.__class__.__name__, "error_msg": msg}


def _run_case_with_repeats(
    case_file: Path,
    repeats: int,
    batch_dir: Path,
    mock_judge: bool,
    target: str,
    debug: bool,
    max_tokens: int = 500,
) -> dict:
    """Run a single case multiple times and calculate metrics."""
    scenario = load_scenario(str(case_file))
    scenario_id = scenario.get("scenario_id", case_file.stem)

    case_dir = batch_dir / scenario_id
    case_dir.mkdir(parents=True, exist_ok=True)

    run_results: list[dict[str, Any]] = []

    for i in range(repeats):
        run_output = case_dir / f"run_{i+1:03d}"
        run_output.mkdir(parents=True, exist_ok=True)

        config = {"mock_judge": mock_judge, "max_tokens": max_tokens}

        try:
            result = run_scenario(
                scenario_path=str(case_file),
                target_name=target,
                output_root=str(run_output.parent),
                config=config,
            )

            # Extract GDPR compliance score if available
            gdpr_score = None
            for score in (getattr(result, "scores", None) or []):
                if score.get("scorer") == "gdpr_compliance":
                    gdpr_score = score
                    break

            run_results.append(
                {
                    "run_id": getattr(result, "run_id", f"run_{i+1:03d}"),
                    "run_dir": str(getattr(result, "run_dir", run_output)),
                    "verdict": gdpr_score.get("verdict") if gdpr_score else None,
                    "signals": gdpr_score.get("signals", []) if gdpr_score else [],
                    "unscored_findings": gdpr_score.get("unscored_findings", []) if gdpr_score else [],
                }
            )

        except Exception as e:
            err = _classify_error(e)
            run_results.append(
                {
                    "run_id": f"failed_{i+1:03d}",
                    "run_dir": str(run_output),
                    "verdict": "UNCLEAR",
                    "signals": [],
                    "error": err,
                }
            )
            print(f"[WARNING] Run {i+1}/{repeats} failed: {err['error_type']} - {err['error_msg']}")
            if debug:
                raise

    metrics = _calculate_case_metrics(run_results, scenario)

    # Ensure error_count is present (tests require it)
    metrics["error_count"] = sum(1 for r in run_results if "error" in r)

    # Expected outcome (support v1 + v2 formats)
    expected = scenario.get("expected_outcome", {}) or {}
    expected_required = expected.get("required_signals", expected.get("signals", [])) or []
    expected_allowed_extra = expected.get("allowed_extra_signals", []) or []

    required_set = set(expected_required)
    allowed_extra_set = set(expected_allowed_extra)
    score_set = required_set | allowed_extra_set

    modal_signals = metrics.get("modal_signals", []) or []
    modal_signals_set = set(modal_signals)

    scored_actual_set = modal_signals_set & score_set
    unscored_signals = sorted(modal_signals_set - score_set)
    missing_required = sorted(required_set - scored_actual_set)

    # Keep these as drift / recall diagnostics (scenario-scoped)
    if score_set:
        metrics["allowed_only_pass"] = modal_signals_set.issubset(score_set)
    if required_set:
        metrics["required_recall_pass"] = required_set.issubset(scored_actual_set)

    metrics["unscored_signal_count"] = len(unscored_signals)
    metrics["has_unscored_signals"] = bool(unscored_signals)

    # Choose unscored_findings from the modal run if present
    unscored_findings: list[str] = []
    if metrics.get("modal_signals") is not None:
        for r in run_results:
            if (r.get("signals") or []) == modal_signals:
                unscored_findings = list(r.get("unscored_findings") or [])
                break

    return {
        "scenario_id": scenario_id,
        "case_file": str(case_file),
        "repeats": repeats,
        "runs": run_results,
        "metrics": metrics,
        # expected sets for reporting
        "expected_required_signals": list(expected_required),
        "expected_allowed_extra_signals": list(expected_allowed_extra),
        # scenario-scoped fields
        "score_set_signals": sorted(score_set),
        "scored_actual_signals": sorted(scored_actual_set),
        "unscored_signals": unscored_signals,
        "unscored_findings": unscored_findings,
        # legacy fields kept (extra_unallowed == out-of-scope extras)
        "missing_required_signals": missing_required,
        "extra_unallowed_signals": unscored_signals,
    }


def _calculate_case_metrics(run_results: list[dict], scenario: dict) -> dict:
    """Calculate repeatability and correctness metrics for a case."""
    verdicts = [r["verdict"] for r in run_results if r.get("verdict") is not None]
    signals_sets = [tuple(sorted(r.get("signals", []) or [])) for r in run_results]

    verdict_counter = Counter(verdicts)
    signals_counter = Counter(signals_sets)

    modal_verdict = verdict_counter.most_common(1)[0][0] if verdict_counter else None
    modal_signals = list(signals_counter.most_common(1)[0][0]) if signals_counter else []

    verdict_repeatability = (verdict_counter.most_common(1)[0][1] / len(run_results)) if verdict_counter else 0.0
    signals_repeatability = (signals_counter.most_common(1)[0][1] / len(run_results)) if signals_counter else 0.0

    metrics: dict[str, Any] = {
        "modal_verdict": modal_verdict,
        "modal_signals": modal_signals,
        "verdict_repeatability": verdict_repeatability,
        "signals_repeatability": signals_repeatability,
        "error_count": sum(1 for r in run_results if "error" in r),
    }

    expected = (scenario.get("expected_outcome", {}) or {}) if scenario else {}
    if not expected:
        return metrics

    expected_verdict = expected.get("verdict")

    # v2 expected sets (preferred for scoring)
    required_signals = set(expected.get("required_signals", expected.get("signals", [])) or [])
    allowed_extra_signals = set(expected.get("allowed_extra_signals", []) or [])
    score_set = required_signals | allowed_extra_signals

    # legacy strict/subset metrics (only if expected.signals exists)
    expected_signals_legacy = set(expected.get("signals", []) or [])

    if expected_verdict and modal_verdict is not None:
        metrics["verdict_correctness"] = (modal_verdict == expected_verdict)

    modal_set = set(modal_signals)

    if expected_signals_legacy:
        metrics["signals_correctness_strict"] = (modal_set == expected_signals_legacy)
        metrics["signals_correctness_subset"] = expected_signals_legacy.issubset(modal_set)

    # scenario-scoped: score only required ∪ allowed_extra
    scored_actual = modal_set & score_set
    unscored = modal_set - score_set

    if required_signals:
        metrics["required_recall_pass"] = required_signals.issubset(scored_actual)
    if score_set:
        metrics["allowed_only_pass"] = modal_set.issubset(score_set)

    metrics["unscored_signal_count"] = len(unscored)
    metrics["has_unscored_signals"] = bool(unscored)

    return metrics


def _calculate_aggregate_metrics(case_results: list[dict]) -> dict:
    """Calculate aggregate metrics across all cases."""
    total_cases = len(case_results)

    verdict_repeatability = [cr["metrics"]["verdict_repeatability"] for cr in case_results]
    signals_repeatability = [cr["metrics"]["signals_repeatability"] for cr in case_results]

    verdict_correctness = [
        cr["metrics"].get("verdict_correctness")
        for cr in case_results
        if "verdict_correctness" in cr.get("metrics", {})
    ]
    signals_strict = [
        cr["metrics"].get("signals_correctness_strict")
        for cr in case_results
        if "signals_correctness_strict" in cr.get("metrics", {})
    ]
    signals_subset = [
        cr["metrics"].get("signals_correctness_subset")
        for cr in case_results
        if "signals_correctness_subset" in cr.get("metrics", {})
    ]

    modal_verdicts = [cr["metrics"].get("modal_verdict") for cr in case_results]
    modal_verdict_counter = Counter(modal_verdicts)

    aggregate: dict[str, Any] = {
        "total_cases": total_cases,
        "mean_verdict_repeatability": (sum(verdict_repeatability) / total_cases) if verdict_repeatability else 0.0,
        "mean_signals_repeatability": (sum(signals_repeatability) / total_cases) if signals_repeatability else 0.0,
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

    required_recall = [
        cr["metrics"].get("required_recall_pass")
        for cr in case_results
        if "required_recall_pass" in cr.get("metrics", {})
    ]
    allowed_only = [
        cr["metrics"].get("allowed_only_pass")
        for cr in case_results
        if "allowed_only_pass" in cr.get("metrics", {})
    ]

    if required_recall:
        aggregate["required_recall_accuracy"] = sum(required_recall) / len(required_recall)
        aggregate["required_recall_case_fail_count"] = sum(1 for passed in required_recall if not passed)
        aggregate["required_recall_missing_count"] = sum(len(cr.get("missing_required_signals", [])) for cr in case_results)

    if allowed_only:
        aggregate["allowed_only_accuracy"] = sum(allowed_only) / len(allowed_only)
        aggregate["allowed_only_case_fail_count"] = sum(1 for passed in allowed_only if not passed)

    # Out-of-scope signal counts (diagnostic)
    aggregate["unscored_signal_case_count"] = sum(
        1 for cr in case_results if cr.get("metrics", {}).get("has_unscored_signals")
    )
    aggregate["unscored_signal_total_count"] = sum(
        cr.get("metrics", {}).get("unscored_signal_count", 0) for cr in case_results
    )

    return aggregate


def _write_batch_report(path: Path, summary: dict) -> None:
    """Write batch report in Markdown format."""
    meta = summary["batch_meta"]
    agg = summary["aggregate_metrics"]
    cases = summary["case_results"]

    lines: list[str] = [
        f"# Batch Calibration Report: {meta['batch_id']}",
        "",
        f"**Timestamp**: {meta['timestamp_utc']}  ",
        f"**Cases Directory**: {meta['cases_dir']}  ",
        f"**Repeats**: {meta['repeats']}  ",
        f"**Mock Judge**: {meta['mock_judge']}  ",
        f"**Target**: {meta['target']}  ",
        f"**Git SHA**: {meta['git_sha']}  ",
        f"**Python**: {meta['python_version']}  ",
        f"**Framework ID**: {meta.get('framework_id', 'gdpr')}  ",
        f"**Taxonomy Version**: {meta.get('taxonomy_version', 'unknown')}  ",
        f"**Rubric ID**: {meta.get('rubric_id', 'unknown')}  ",
        f"**Max Tokens**: {meta.get('max_tokens', 'unknown')}  ",
        "",
        "---",
        "",
        "## Aggregate Metrics",
        "",
        "Scenario-scoped scoring: only signals in (required ∪ allowed_extra) are in-scope; other signals are recorded as out-of-scope drift.",
        "",
        f"- **Total Cases**: {agg['total_cases']}",
        f"- **Mean Verdict Repeatability**: {agg['mean_verdict_repeatability']:.2%}",
        f"- **Mean Signals Repeatability**: {agg['mean_signals_repeatability']:.2%}",
        f"- **Verdict Pass Count (NO_VIOLATION)**: {agg['verdict_pass_count']}",
        f"- **Verdict Fail Count (VIOLATION)**: {agg['verdict_fail_count']}",
        f"- **Verdict Unclear Count**: {agg['verdict_unclear_count']}",
    ]

    if "verdict_accuracy" in agg:
        lines.append(f"- **Verdict Accuracy**: {agg['verdict_accuracy']:.2%}")
    if "signals_strict_accuracy" in agg:
        lines.append(f"- **Signals Strict Accuracy**: {agg['signals_strict_accuracy']:.2%}")
    if "signals_subset_accuracy" in agg:
        lines.append(f"- **Signals Subset Accuracy**: {agg['signals_subset_accuracy']:.2%}")
    if "required_recall_accuracy" in agg:
        lines.append(f"- **Required Recall Accuracy**: {agg['required_recall_accuracy']:.2%}")
    if "allowed_only_accuracy" in agg:
        lines.append(f"- **Allowed Only Accuracy (no out-of-scope extras)**: {agg['allowed_only_accuracy']:.2%}")

    lines.extend(
        [
            "",
            "### Signal Analysis Counts",
            f"- **Required Recall Missing Count**: {agg.get('required_recall_missing_count', 0)} (total missing signals across all cases)",
            f"- **Required Recall Case Fail Count**: {agg.get('required_recall_case_fail_count', 0)} (cases with missing required signals)",
            f"- **Allowed Only Case Fail Count**: {agg.get('allowed_only_case_fail_count', 0)} (cases with out-of-scope extra signals)",
            f"- **Unscored Signal Case Count**: {agg.get('unscored_signal_case_count', 0)} (cases with out-of-scope signals)",
            f"- **Unscored Signal Total Count**: {agg.get('unscored_signal_total_count', 0)} (total out-of-scope signals)",
            "",
            "---",
            "",
            "## Case Results",
            "",
        ]
    )

    for case in cases:
        m = case["metrics"]
        lines.extend(
            [
                f"### {case['scenario_id']}",
                "",
                f"- **Repeats**: {case['repeats']}",
                f"- **Modal Verdict**: {m.get('modal_verdict')}",
                f"- **Modal Signals**: {', '.join(m.get('modal_signals') or []) if (m.get('modal_signals') or []) else 'none'}",
                f"- **Verdict Repeatability**: {m['verdict_repeatability']:.2%}",
                f"- **Signals Repeatability**: {m['signals_repeatability']:.2%}",
                f"- **Error Count**: {m.get('error_count', 0)}",
            ]
        )

        if "verdict_correctness" in m:
            lines.append(f"- **Verdict Correctness**: {'✓ PASS' if m['verdict_correctness'] else '✗ FAIL'}")
        if "signals_correctness_strict" in m:
            lines.append(f"- **Signals Strict**: {'✓ PASS' if m['signals_correctness_strict'] else '✗ FAIL'}")
        if "signals_correctness_subset" in m:
            lines.append(f"- **Signals Subset**: {'✓ PASS' if m['signals_correctness_subset'] else '✗ FAIL'}")
        if "required_recall_pass" in m:
            lines.append(f"- **Required Recall**: {'✓ PASS' if m['required_recall_pass'] else '✗ FAIL'}")
        if "allowed_only_pass" in m:
            lines.append(f"- **Allowed Only**: {'✓ PASS' if m['allowed_only_pass'] else '✗ FAIL'}")

        if case.get("expected_required_signals"):
            lines.append(f"- **Expected Required**: {', '.join(case['expected_required_signals'])}")
        if case.get("expected_allowed_extra_signals"):
            lines.append(f"- **Allowed Extra**: {', '.join(case['expected_allowed_extra_signals'])}")
        if case.get("missing_required_signals"):
            lines.append(f"- **Missing Required**: {', '.join(case['missing_required_signals'])}")

        if case.get("unscored_signals"):
            lines.append(f"- **Unscored Signals (out of scope)**: {', '.join(case['unscored_signals'])}")
        elif case.get("extra_unallowed_signals"):
            lines.append(f"- **Unscored Signals (out of scope)**: {', '.join(case['extra_unallowed_signals'])}")

        if case.get("unscored_findings"):
            lines.append(f"- **Unscored Findings**: {', '.join(case['unscored_findings'])}")

        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _get_git_sha() -> str:
    """Get current git SHA."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return r.stdout.strip()
    except Exception:
        return "unknown"


def _get_python_version() -> str:
    """Get Python version."""
    import sys

    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
