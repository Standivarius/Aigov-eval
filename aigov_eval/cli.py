"""CLI entrypoint."""

from __future__ import annotations

import argparse
import os

from .env import init_env
from .runner import run_scenario
from .targets import TARGETS


ERROR_MISSING_KEY = (
    "OPENROUTER_API_KEY is required. "
    "Set it in the environment or in a local .env file (see .env.example)."
)


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
    run_parser.add_argument("--debug", action="store_true", help="Print .env diagnostics")

    args = parser.parse_args(argv)

    if args.command != "run":
        parser.print_help()
        return 1

    init_env(debug=args.debug)

    if args.target == "mock-llm" and not os.getenv("OPENROUTER_API_KEY"):
        print(ERROR_MISSING_KEY)
        return 2

    config = {
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "seed": args.seed,
        "leaky": args.leaky,
        "leak_profile": args.leak_profile,
        "leak_after": args.leak_after,
    }

    result = run_scenario(
        scenario_path=args.scenario,
        target_name=args.target,
        output_root=args.out,
        config=config,
    )

    print(f"Run {result.run_id} complete. Outputs in {result.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
