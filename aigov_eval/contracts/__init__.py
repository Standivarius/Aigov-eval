"""Vendored contract helpers."""

from __future__ import annotations

from pathlib import Path


def get_behaviour_schema_path() -> Path:
    """Return the vendored behaviour_json schema path."""
    return Path(__file__).resolve().parent / "behaviour_json_v0_phase0.schema.json"
