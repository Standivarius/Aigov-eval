"""Taxonomy loader for signals and frameworks."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    """
    Load signals taxonomy from taxonomy/signals.json.

    Returns:
        dict with keys:
            - version: taxonomy version string
            - description: taxonomy description
            - last_updated: last update date
            - signals: list of signal definitions
            - allowed_signal_ids: set of valid signal IDs
            - signal_metadata: dict mapping signal ID to metadata
    """
    taxonomy_path = Path(__file__).parent.parent / "taxonomy" / "signals.json"

    if not taxonomy_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found: {taxonomy_path}")

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        raw_taxonomy = json.load(f)

    # Extract signal IDs and build metadata map
    allowed_signal_ids = set()
    signal_metadata = {}

    for signal in raw_taxonomy.get("signals", []):
        signal_id = signal.get("id")
        if signal_id:
            allowed_signal_ids.add(signal_id)
            signal_metadata[signal_id] = {
                "title": signal.get("title"),
                "description": signal.get("description"),
                "gdpr_ref": signal.get("gdpr_ref", []),
                "severity": signal.get("severity"),
            }

    return {
        "version": raw_taxonomy.get("version", "unknown"),
        "description": raw_taxonomy.get("description", ""),
        "last_updated": raw_taxonomy.get("last_updated", ""),
        "signals": raw_taxonomy.get("signals", []),
        "allowed_signal_ids": allowed_signal_ids,
        "signal_metadata": signal_metadata,
    }


def get_taxonomy_version() -> str:
    """Get taxonomy version string."""
    return load_taxonomy()["version"]


def get_allowed_signal_ids() -> set[str]:
    """Get set of allowed signal IDs."""
    return load_taxonomy()["allowed_signal_ids"]


def get_signal_metadata(signal_id: str) -> dict[str, Any] | None:
    """Get metadata for a specific signal ID."""
    return load_taxonomy()["signal_metadata"].get(signal_id)


# Known synonyms for backward compatibility
# Maps old/non-canonical signal names to canonical taxonomy IDs
SIGNAL_SYNONYMS = {
    "dpo_absence": "inadequate_dpo",
    "data_minimization_violation": "data_minimization_breach",
    "excessive_data_retention": "retention_violation",
    "subject_rights_denial": "rights_violation",
    "cross_border_transfer_violation": "international_transfer_violation",
    "automated_decision_making": "profiling_without_safeguards",
}


def normalize_signal(signal: str) -> str | None:
    """
    Normalize a signal to its canonical taxonomy ID.

    Args:
        signal: Signal name (possibly non-canonical)

    Returns:
        Canonical signal ID if valid/known, None if unknown
    """
    allowed_ids = get_allowed_signal_ids()

    # Already canonical
    if signal in allowed_ids:
        return signal

    # Known synonym
    if signal in SIGNAL_SYNONYMS:
        return SIGNAL_SYNONYMS[signal]

    # Unknown signal
    return None
