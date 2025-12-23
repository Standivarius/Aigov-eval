"""CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import os

from .batch_runner import run_batch
from .env import init_env
from .runner import run_scenario
from .targets import TARGETS


ERROR_MISSING_KEY = (
    "OPENROUTER_API_KEY is required. "
    "Set it in the environment or in a local .env file (see .env.example)."
)


def _load_target_config(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        if os.path.exists(raw):
            with open(raw, "r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
        else:
            data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "Invalid --target-config-json: "
            f"{exc.msg} (hint: on Windows use --target-config-file <path>)"
        ) from exc

    if not isinstance(data, dict):
        raise SystemExit("Invalid --target-config-json: expected a JSON object")
    return data


def _load_target_config_file(path: str | None) -> dict:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --target-config-file JSON: {exc.msg}") from exc
    except OSError as exc:
        raise SystemExit(f"Failed to read --target-config-file: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit("Invalid --target-config-file: expected a JSON object")
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="aigov_eval")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a scenario")
    run_parser.add_argument("--scenario", required=True, help="Path to scenario YAML/JSON")
    run_parser.add_argument("--target", required=True, choices=sorted(TARGETS.keys()))
    run_parser.add_argument("--out", required=True, help="Output directory root")
    run_parser.add_argument("--temperature", type=float, default=None)
    run_parser.add_argument("--max-tokens", type=int, default=None)
    run_parser.add_argument("--seed", type=int, default=None)
    run_parser.add_argument("--leaky", action="store_true", help="Enable deterministic leaky mode")
    run_parser.add_argument(
        "--leak-profile",
        choices=["pii_basic", "special_category_basic"],
        default="pii_basic",
        help="Leak profile for deterministic mock mode",
    )
    run_parser.add_argument(
        "--leak-after",
        type=int,
        default=2,
        help="Leak on the Nth repeated request for the same person and field",
    )
    run_parser.add_argument(
        "--target-config-json",
        default=None,
        help="JSON string for target-specific config",
    )
    run_parser.add_argument(
        "--target-config-file",
        default=None,
        help="Path to JSON file for target-specific config",
    )
    run_parser.add_argument("--debug", action="store_true", help="Print .env diagnostics")

    batch_parser = subparsers.add_parser("batch-run", help="Run batch calibration test")
    batch_parser.add_argument("--cases-dir", required=True, help="Directory containing case JSON files")
    batch_parser.add_argument("--repeats", type=int, default=5, help="Number of repeats per case")
    batch_parser.add_argument("--out", required=True, help="Output directory root")
    batch_parser.add_argument("--mock-judge", action="store_true", help="Use mock judge (deterministic)")
    batch_parser.add_argument("--target", default="scripted", help="Target name (default: scripted)")
    batch_parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    init_env(debug=getattr(args, "debug", False))

    if args.command == "batch-run":
        # Batch run command
        try:
            run_batch(
                cases_dir=args.cases_dir,
                repeats=args.repeats,
                output_root=args.out,
                mock_judge=args.mock_judge,
                target=args.target,
                debug=args.debug,
            )
            return 0
        except Exception as exc:
            print(f"Batch run failed: {exc}")
            return 2

    # Single run command
    if args.target == "mock-llm" and not os.getenv("OPENROUTER_API_KEY"):
        print(ERROR_MISSING_KEY)
        return 2

    config = {}
    config.update(_load_target_config_file(args.target_config_file))
    config.update(_load_target_config(args.target_config_json))
    config.update(
        {
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "seed": args.seed,
            "leaky": args.leaky,
            "leak_profile": args.leak_profile,
            "leak_after": args.leak_after,
        }
    )

    try:
        result = run_scenario(
            scenario_path=args.scenario,
            target_name=args.target,
            output_root=args.out,
            config=config,
        )
    except ValueError as exc:
        print(str(exc))
        return 2

    print(f"Run {result.run_id} complete. Outputs in {result.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
