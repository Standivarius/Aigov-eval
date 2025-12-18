"""CLI entrypoint."""

from __future__ import annotations

import argparse
import sys

from .runner import run_scenario
from .targets import TARGETS


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
    run_parser.add_argument("--leaky", action="store_true", help="Enable leaky system prompt")

    args = parser.parse_args(argv)

    if args.command != "run":
        parser.print_help()
        return 1

    config = {
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "seed": args.seed,
        "leaky": args.leaky,
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
