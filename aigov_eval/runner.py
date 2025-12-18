"""Minimal transcript-first runner."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .evidence import build_evidence_pack, write_evidence_pack
from .loader import load_scenario
from .scorers import score_pii_disclosure, score_special_category_leak
from .targets import get_target


@dataclass
class RunResult:
    run_id: str
    run_dir: Path
    transcript: List[Dict[str, Any]]
    scores: List[Dict[str, Any]]
    run_meta: Dict[str, Any]


def run_scenario(
    scenario_path: str,
    target_name: str,
    output_root: str,
    config: Dict[str, Any],
) -> RunResult:
    scenario = load_scenario(scenario_path)
    scenario["source_path"] = scenario_path

    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    run_id = _build_run_id()
    run_dir = output_root_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    target_cls = get_target(target_name)
    target = target_cls(scenario, config)

    runner_config = {
        "target": target_name,
        "model": getattr(target, "model", None),
        "base_url": getattr(target, "base_url", None),
        "temperature": config.get("temperature"),
        "max_tokens": config.get("max_tokens"),
        "seed": config.get("seed"),
        "leaky": bool(config.get("leaky")),
    }

    transcript: List[Dict[str, Any]] = []
    messages: List[Dict[str, str]] = []

    auditor_seed = scenario.get("auditor_seed")
    if auditor_seed:
        messages.append({"role": "system", "content": auditor_seed})

    turn_index = 0
    started_at = _utc_now()

    for turn in scenario.get("turns", []):
        role = turn.get("role", "user")
        content = turn.get("content", "")
        messages.append({"role": role, "content": content})
        transcript.append(_entry(turn_index, role, content))
        turn_index += 1

        if role != "user":
            continue

        response = target.respond(messages)
        assistant_content = response.get("content", "")
        metadata = response.get("metadata")

        messages.append({"role": "assistant", "content": assistant_content})
        transcript.append(_entry(turn_index, "assistant", assistant_content, metadata))
        turn_index += 1

    scores = [
        score_pii_disclosure(transcript),
        score_special_category_leak(transcript),
    ]

    finished_at = _utc_now()
    run_meta = {
        "run_id": run_id,
        "scenario_path": scenario_path,
        "scenario_id": scenario.get("scenario_id"),
        "target": target_name,
        "runner_config": runner_config,
        "started_at": started_at,
        "finished_at": finished_at,
    }

    _write_json(run_dir / "transcript.json", transcript)
    _write_json(run_dir / "scores.json", scores)
    _write_json(run_dir / "run_meta.json", run_meta)

    evidence_pack = build_evidence_pack(
        scenario=scenario,
        transcript=transcript,
        scores=scores,
        runner_config=runner_config,
    )
    write_evidence_pack(str(run_dir / "evidence_pack.json"), evidence_pack)

    return RunResult(
        run_id=run_id,
        run_dir=run_dir,
        transcript=transcript,
        scores=scores,
        run_meta=run_meta,
    )


def _entry(
    turn_index: int,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry = {
        "turn_index": turn_index,
        "role": role,
        "content": content,
        "timestamp": _utc_now(),
    }
    if metadata:
        entry["metadata"] = metadata
    return entry


def _write_json(path: Path, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{stamp}_{suffix}"
