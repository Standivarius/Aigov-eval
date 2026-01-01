"""Minimal offline judge runner that reads fixture inputs and produces schema-valid judge_output.json.

This module provides a standalone offline judge runner that:
1. Reads calibration case fixtures from a directory
2. Extracts expected outcomes from fixture metadata
3. Generates internal judge output (preserves judge logic)
4. Maps internal output to behaviour_json_v0_phase0 schema (deterministic mapping)
5. Validates and writes schema-compliant judge_output.json files
6. Does NOT touch live execution, Petri, or Inspect

The mapping step is explicit and separated from judge logic to maintain clear boundaries.

Usage:
    python -m aigov_eval.offline_judge_runner --fixtures-dir cases/calibration --output-dir output/judge_outputs
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .judge_output_mapper import map_and_validate
from .taxonomy import get_allowed_signal_ids, validate_signals


def generate_judge_output(fixture_path: Path) -> dict[str, Any]:
    """
    Generate internal judge output from a fixture file.

    This function produces the INTERNAL judge output format, which is then
    mapped to behaviour_json_v0_phase0 schema by the caller.

    Args:
        fixture_path: Path to calibration case fixture JSON file

    Returns:
        Internal judge output dictionary:
        {
            "verdict": "VIOLATION" | "NO_VIOLATION" | "UNCLEAR",
            "signals": ["signal1", "signal2", ...],
            "citations": ["Art. 5(1)(a)", ...],
            "rationale": ["reason1", "reason2", ...],
            "judge_meta": {
                "model": "offline-judge-v1",
                "temperature": 0.0,
                "top_p": 1.0,
                "base_url": "offline",
                "mock": true,
                "timestamp_utc": "ISO8601 timestamp",
                "source_fixture": "fixture filename",
                "scenario_id": "scenario_id"
            }
        }

    Note: This is NOT the final output format. The caller should use
    judge_output_mapper.map_and_validate() to produce schema-compliant output.
    """
    # Load fixture
    with open(fixture_path, 'r', encoding='utf-8') as f:
        fixture = json.load(f)

    scenario_id = fixture.get("scenario_id", "unknown")
    expected_outcome = fixture.get("expected_outcome", {})

    # Extract verdict
    verdict = expected_outcome.get("verdict", "NO_VIOLATION")

    # Extract signals - support both v2 (required_signals + allowed_extra_signals) and legacy formats
    signals = []
    if "required_signals" in expected_outcome:
        # V2 format: combine required and allowed extra signals
        signals = list(expected_outcome.get("required_signals", []))
        signals.extend(expected_outcome.get("allowed_extra_signals", []))
    else:
        # Legacy format: use signals field directly
        signals = expected_outcome.get("signals", [])

    # Validate signals against taxonomy
    allowed_signals = get_allowed_signal_ids()
    validated = validate_signals(signals, allowed_signals)

    # Extract citations
    citations = expected_outcome.get("gdpr_citations", [])

    # Generate rationale from fixture metadata
    rationale = expected_outcome.get("rationale", [])
    if not rationale:
        # Generate default rationale if none provided
        title = fixture.get("title", "Unknown scenario")
        rationale = [
            f"Offline judge output for scenario: {title}",
            f"Based on expected outcome from fixture: {fixture_path.name}"
        ]

    # Build judge metadata
    judge_meta = {
        "model": "offline-judge-v1",
        "temperature": 0.0,
        "top_p": 1.0,
        "base_url": "offline",
        "mock": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_fixture": fixture_path.name,
        "scenario_id": scenario_id
    }

    # Build output
    output = {
        "verdict": verdict,
        "signals": validated["signals"],
        "citations": citations,
        "rationale": rationale,
        "judge_meta": judge_meta
    }

    # Include unrecognized signals if any (for debugging)
    if validated["other_signals"]:
        output["_warnings"] = {
            "unrecognized_signals": validated["other_signals"],
            "message": "These signals are not in the taxonomy and were excluded"
        }

    return output


def run_offline_judge(
    fixtures_dir: Path,
    output_dir: Path,
    verbose: bool = False
) -> dict[str, Any]:
    """
    Run offline judge on all fixtures in a directory.

    Args:
        fixtures_dir: Directory containing fixture JSON files
        output_dir: Directory to write judge_output.json files
        verbose: Print progress messages

    Returns:
        Summary dictionary with processed count and any errors
    """
    fixtures_dir = Path(fixtures_dir)
    output_dir = Path(output_dir)

    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Fixtures directory not found: {fixtures_dir}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all JSON fixtures
    fixture_files = sorted(fixtures_dir.glob("*.json"))

    if not fixture_files:
        print(f"Warning: No JSON fixtures found in {fixtures_dir}", file=sys.stderr)
        return {"processed": 0, "errors": []}

    processed = 0
    errors = []

    for fixture_path in fixture_files:
        try:
            if verbose:
                print(f"Processing: {fixture_path.name}")

            # Step 1: Generate internal judge output (preserves judge logic)
            internal_output = generate_judge_output(fixture_path)

            # Step 2: Map to behaviour_json_v0_phase0 schema (deterministic mapping)
            # This is the explicit, named mapping step
            scenario_id = internal_output.get("judge_meta", {}).get("scenario_id", "unknown")
            behaviour_json_output = map_and_validate(
                internal_output,
                scenario_id=scenario_id,
                fail_on_invalid=True  # Fail closed if schema validation fails
            )

            # Step 3: Write schema-compliant output
            output_file = output_dir / f"{fixture_path.stem}_judge_output.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(behaviour_json_output, f, indent=2, ensure_ascii=False)

            if verbose:
                print(f"  → {output_file.name}")
                print(f"     Rating: {behaviour_json_output['rating']}")
                print(f"     Signals: {', '.join(behaviour_json_output['signals']) if behaviour_json_output['signals'] else 'none'}")

            processed += 1

        except Exception as e:
            error_msg = f"Error processing {fixture_path.name}: {str(e)}"
            errors.append(error_msg)
            print(f"ERROR: {error_msg}", file=sys.stderr)

    # Write summary
    summary = {
        "processed": processed,
        "total_fixtures": len(fixture_files),
        "errors": errors,
        "output_dir": str(output_dir),
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }

    summary_file = output_dir / "_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    if verbose:
        print(f"\nSummary:")
        print(f"  Processed: {processed}/{len(fixture_files)} fixtures")
        print(f"  Output dir: {output_dir}")
        if errors:
            print(f"  Errors: {len(errors)}")

    return summary


def main():
    """CLI entry point for offline judge runner."""
    parser = argparse.ArgumentParser(
        description="Minimal offline judge runner - reads fixture inputs and produces schema-valid judge_output.json"
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=Path("cases/calibration"),
        help="Directory containing fixture JSON files (default: cases/calibration)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory to write judge_output.json files"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress messages"
    )

    args = parser.parse_args()

    try:
        summary = run_offline_judge(
            fixtures_dir=args.fixtures_dir,
            output_dir=args.output_dir,
            verbose=args.verbose
        )

        # Exit with error code if there were errors
        if summary["errors"]:
            sys.exit(1)

    except Exception as e:
        print(f"FATAL: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
