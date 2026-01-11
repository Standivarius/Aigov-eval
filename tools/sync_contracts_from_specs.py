"""Sync contracts from AiGov-specs into PE."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync contracts from AiGov-specs.")
    parser.add_argument("--specs-root", default="..\\AiGov-specs", help="Path to AiGov-specs repo root")
    return parser.parse_args()


def _build_copy_plan(specs_root: Path, repo_root: Path) -> list[tuple[Path, Path]]:
    taxonomy_src_dir = specs_root / "docs" / "contracts" / "taxonomy"
    taxonomy_dest_dir = repo_root / "aigov_eval" / "taxonomy" / "contracts"

    return [
        (taxonomy_src_dir / "signals.json", taxonomy_dest_dir / "signals.json"),
        (taxonomy_src_dir / "verdicts.json", taxonomy_dest_dir / "verdicts.json"),
        (
            specs_root / "schemas" / "behaviour_json_v0_phase0.schema.json",
            repo_root / "aigov_eval" / "contracts" / "behaviour_json_v0_phase0.schema.json",
        ),
    ]


def main() -> int:
    args = _parse_args()
    specs_root = Path(args.specs_root)
    repo_root = Path(__file__).resolve().parents[1]

    copy_plan = _build_copy_plan(specs_root, repo_root)
    missing = [str(src) for src, _ in copy_plan if not src.exists()]
    if missing:
        print("ERROR: missing source files:")
        for src in missing:
            print(f"  {src}")
        return 2

    for src_path, dest_path in copy_plan:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dest_path)
        print(f"copied {src_path} -> {dest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
