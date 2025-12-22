#!/usr/bin/env python3
"""
Golden Set Evaluation Matrix Runner

Runs golden set test cases across multiple engines with seeded repetitions,
generating comprehensive evaluation reports.

Usage:
    python tools/run_mvp_eval_matrix.py --cases-dir cases --engines mock,scripted
    python tools/run_mvp_eval_matrix.py --help
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import aigov_eval components
try:
    from aigov_eval.runner import run_scenario
    from aigov_eval.targets import TARGETS
    HAS_AIGOV_EVAL = True
except ImportError:
    HAS_AIGOV_EVAL = False
    print("WARNING: aigov_eval module not found. Some features may be limited.", file=sys.stderr)


class EvalMatrixRunner:
    """Orchestrates evaluation runs across cases, engines, and repetitions."""

    def __init__(
        self,
        cases_dir: Path,
        output_dir: Path,
        engines: List[str],
        repetitions: int = 3,
        base_seed: int = 42,
    ):
        """
        Initialize the matrix runner.

        Args:
            cases_dir: Directory containing case JSON files
            output_dir: Directory for evaluation outputs
            engines: List of target engine names (e.g., ['mock', 'scripted'])
            repetitions: Number of seeded runs per case
            base_seed: Base seed for deterministic runs
        """
        self.cases_dir = cases_dir
        self.output_dir = output_dir
        self.engines = engines
        self.repetitions = repetitions
        self.base_seed = base_seed

        self.results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def validate_inputs(self) -> None:
        """Validate that all required inputs exist and are valid."""
        errors = []

        # Check cases directory exists
        if not self.cases_dir.exists():
            errors.append(f"Cases directory not found: {self.cases_dir}")
        elif not self.cases_dir.is_dir():
            errors.append(f"Cases path is not a directory: {self.cases_dir}")
        else:
            # Check for case files
            case_files = list(self.cases_dir.glob("*.json"))
            if not case_files:
                errors.append(f"No case files (*.json) found in: {self.cases_dir}")

        # Check engines are valid
        if HAS_AIGOV_EVAL:
            invalid_engines = [e for e in self.engines if e not in TARGETS]
            if invalid_engines:
                errors.append(
                    f"Invalid engines: {invalid_engines}. "
                    f"Valid options: {sorted(TARGETS.keys())}"
                )

        # Check repetitions is positive
        if self.repetitions < 1:
            errors.append(f"Repetitions must be >= 1, got: {self.repetitions}")

        if errors:
            print("ERROR: Input validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)

        print(f"✓ Validation passed")
        print(f"  Cases dir: {self.cases_dir}")
        print(f"  Engines: {', '.join(self.engines)}")
        print(f"  Repetitions: {self.repetitions}")

    def load_cases(self) -> List[Path]:
        """Load all case files from cases directory."""
        case_files = sorted(self.cases_dir.glob("*.json"))

        if not case_files:
            print(f"ERROR: No case files found in {self.cases_dir}", file=sys.stderr)
            sys.exit(1)

        print(f"\n✓ Found {len(case_files)} case file(s)")
        return case_files

    def run_matrix(self) -> None:
        """Execute the evaluation matrix: all cases × engines × repetitions."""
        cases = self.load_cases()

        total_runs = len(cases) * len(self.engines) * self.repetitions
        print(f"\n⚙ Running {total_runs} evaluations...")
        print(f"   {len(cases)} cases × {len(self.engines)} engines × {self.repetitions} reps\n")

        run_count = 0
        for case_path in cases:
            case_id = case_path.stem

            for engine in self.engines:
                for rep in range(self.repetitions):
                    run_count += 1
                    seed = self.base_seed + rep

                    print(f"[{run_count}/{total_runs}] {case_id} | {engine} | rep={rep+1} (seed={seed})")

                    try:
                        result = self._run_single_eval(case_path, engine, seed, rep)
                        self.results.append(result)
                        status = result.get("status", "unknown")
                        print(f"  → {status}")
                    except Exception as e:
                        error = {
                            "case_id": case_id,
                            "engine": engine,
                            "repetition": rep,
                            "seed": seed,
                            "error": str(e),
                            "timestamp": self._utc_now(),
                        }
                        self.errors.append(error)
                        print(f"  → ERROR: {e}")

        print(f"\n✓ Completed {len(self.results)} runs")
        if self.errors:
            print(f"⚠ {len(self.errors)} errors occurred")

    def _run_single_eval(
        self,
        case_path: Path,
        engine: str,
        seed: int,
        repetition: int,
    ) -> Dict[str, Any]:
        """Run a single evaluation."""
        case_id = case_path.stem

        # Load case metadata
        with open(case_path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        if not HAS_AIGOV_EVAL:
            # Fallback: just record the configuration without actually running
            return {
                "case_id": case_id,
                "engine": engine,
                "seed": seed,
                "repetition": repetition,
                "status": "skipped_no_runner",
                "timestamp": self._utc_now(),
                "scenario_id": case_data.get("scenario_id"),
                "category": case_data.get("category"),
            }

        # Create output directory for this run
        run_output_dir = self.output_dir / "runs" / f"{case_id}_{engine}_rep{repetition:02d}"

        # Configure the run
        config = {
            "seed": seed,
            "temperature": 0.0,  # Deterministic
        }

        # Run the scenario
        try:
            run_result = run_scenario(
                scenario_path=str(case_path),
                target_name=engine,
                output_root=str(run_output_dir),
                config=config,
            )

            # Extract scores
            scores = run_result.scores if hasattr(run_result, 'scores') else []

            # Determine status based on scores
            status = "pass"
            if any(score.get("verdict") == "FAIL" for score in scores):
                status = "fail"

            return {
                "case_id": case_id,
                "scenario_id": case_data.get("scenario_id"),
                "engine": engine,
                "seed": seed,
                "repetition": repetition,
                "status": status,
                "run_id": run_result.run_id if hasattr(run_result, 'run_id') else None,
                "run_dir": str(run_result.run_dir) if hasattr(run_result, 'run_dir') else None,
                "scores": scores,
                "timestamp": self._utc_now(),
                "category": case_data.get("category"),
                "expected_verdict": case_data.get("expected_outcome", {}).get("verdict"),
            }

        except Exception as e:
            # Re-raise to be caught by the outer handler
            raise RuntimeError(f"Run failed: {e}") from e

    def write_outputs(self) -> None:
        """Write evaluation results in multiple formats."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Write detailed JSON results
        json_path = self.output_dir / "results.json"
        self._write_json(json_path, {
            "metadata": {
                "generated_at": self._utc_now(),
                "cases_dir": str(self.cases_dir),
                "engines": self.engines,
                "repetitions": self.repetitions,
                "base_seed": self.base_seed,
                "total_runs": len(self.results),
                "total_errors": len(self.errors),
            },
            "results": self.results,
            "errors": self.errors,
        })
        print(f"✓ Wrote detailed results: {json_path}")

        # Write CSV summary
        csv_path = self.output_dir / "results.csv"
        self._write_csv(csv_path)
        print(f"✓ Wrote CSV summary: {csv_path}")

        # Write Markdown summary
        md_path = self.output_dir / "summary.md"
        self._write_markdown(md_path)
        print(f"✓ Wrote Markdown summary: {md_path}")

    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Write JSON file with pretty formatting."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False, ensure_ascii=False)

    def _write_csv(self, path: Path) -> None:
        """Write results as CSV."""
        if not self.results:
            return

        fieldnames = [
            "case_id",
            "scenario_id",
            "engine",
            "repetition",
            "seed",
            "status",
            "category",
            "expected_verdict",
            "run_id",
            "timestamp",
        ]

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self.results)

    def _write_markdown(self, path: Path) -> None:
        """Write evaluation summary as Markdown."""
        lines = []
        lines.append("# Golden Set Evaluation Summary")
        lines.append("")
        lines.append(f"**Generated:** {self._utc_now()}")
        lines.append(f"**Cases Directory:** `{self.cases_dir}`")
        lines.append(f"**Engines:** {', '.join(self.engines)}")
        lines.append(f"**Repetitions per case:** {self.repetitions}")
        lines.append("")

        # Overall statistics
        lines.append("## Overall Statistics")
        lines.append("")
        lines.append(f"- **Total runs:** {len(self.results)}")
        lines.append(f"- **Successful:** {len([r for r in self.results if r.get('status') not in ['error', 'skipped_no_runner']])}")
        lines.append(f"- **Failed/Errors:** {len(self.errors)}")
        lines.append("")

        # Results by case
        lines.append("## Results by Case")
        lines.append("")

        by_case = defaultdict(list)
        for result in self.results:
            by_case[result["case_id"]].append(result)

        for case_id in sorted(by_case.keys()):
            case_results = by_case[case_id]
            lines.append(f"### {case_id}")
            lines.append("")
            lines.append("| Engine | Rep | Seed | Status | Expected Verdict |")
            lines.append("|--------|-----|------|--------|------------------|")

            for result in case_results:
                engine = result.get("engine", "N/A")
                rep = result.get("repetition", 0) + 1
                seed = result.get("seed", "N/A")
                status = result.get("status", "unknown")
                expected = result.get("expected_verdict", "N/A")
                lines.append(f"| {engine} | {rep} | {seed} | {status} | {expected} |")
            lines.append("")

        # Errors (if any)
        if self.errors:
            lines.append("## Errors")
            lines.append("")
            for error in self.errors:
                case_id = error.get("case_id", "unknown")
                engine = error.get("engine", "unknown")
                rep = error.get("repetition", 0) + 1
                msg = error.get("error", "unknown error")
                lines.append(f"- **{case_id}** (engine={engine}, rep={rep}): {msg}")
            lines.append("")

        # Write markdown file
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def _utc_now() -> str:
        """Return current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run golden set evaluation across multiple engines with seeded repetitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all cases with mock engine, 3 repetitions
  python tools/run_mvp_eval_matrix.py --cases-dir cases --engines mock

  # Run with multiple engines
  python tools/run_mvp_eval_matrix.py --cases-dir cases --engines mock,scripted --repetitions 5

  # Custom output directory
  python tools/run_mvp_eval_matrix.py --cases-dir cases --engines mock --output-dir my_reports
        """,
    )

    parser.add_argument(
        "--cases-dir",
        type=Path,
        required=True,
        help="Directory containing test case JSON files (e.g., cases/)",
    )

    parser.add_argument(
        "--engines",
        type=str,
        required=True,
        help="Comma-separated list of engines to test (e.g., 'mock,scripted')",
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Number of seeded repetitions per case (default: 3)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Output directory for evaluation reports (default: reports/)",
    )

    parser.add_argument(
        "--base-seed",
        type=int,
        default=42,
        help="Base seed for deterministic runs (default: 42)",
    )

    args = parser.parse_args()

    # Parse engines list
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    if not engines:
        print("ERROR: No engines specified. Use --engines mock,scripted", file=sys.stderr)
        return 1

    # Create runner
    runner = EvalMatrixRunner(
        cases_dir=args.cases_dir,
        output_dir=args.output_dir,
        engines=engines,
        repetitions=args.repetitions,
        base_seed=args.base_seed,
    )

    # Validate inputs
    try:
        runner.validate_inputs()
    except SystemExit:
        return 1

    # Run matrix
    runner.run_matrix()

    # Write outputs
    runner.write_outputs()

    # Return exit code based on errors
    if runner.errors:
        print(f"\n⚠ Evaluation completed with {len(runner.errors)} errors", file=sys.stderr)
        return 1

    print("\n✓ Evaluation completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
