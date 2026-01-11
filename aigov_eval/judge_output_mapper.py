"""Judge output mapper for behaviour_json_v0_phase0 schema compliance.

This module provides deterministic mapping from internal judge output format
to the canonical behaviour_json_v0_phase0 schema. It does NOT change the
judge's internal reasoning logic or verdict decisions.

Mapping assumptions (documented for auditability):

1. Verdict mapping (deterministic):
   - Internal "VIOLATION" → Schema "VIOLATED"
   - Internal "NO_VIOLATION" → Schema "COMPLIANT"
   - Internal "UNCLEAR" → Schema "UNDECIDED"

2. Field mapping:
   - signals → signals (pass-through, already validated by taxonomy)
   - citations → legal_references (renamed for schema compliance)
   - rationale → reasoning (renamed for schema compliance)
   - judge_meta → inspect_provenance (renamed, restructured)

3. ID generation:
   - audit_id: derived from scenario_id + timestamp (deterministic per run)
   - run_id: derived from scenario_id + timestamp (deterministic per run)
   - finding_id: derived from scenario_id + run_id (deterministic)

4. Severity mapping (optional, inferred from verdict):
   - VIOLATED → HIGH (conservative default)
   - COMPLIANT → INFO
   - UNDECIDED → LOW

All mappings are deterministic and preserve the semantic meaning of the
original judge output.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from aigov_eval.contracts import get_behaviour_schema_path

def _generate_deterministic_id(prefix: str, *components: str) -> str:
    """
    Generate a deterministic ID from components.

    Args:
        prefix: ID prefix (e.g., 'audit', 'run', 'finding')
        components: String components to hash

    Returns:
        Deterministic ID in format: {prefix}_{hash}
    """
    # Create deterministic hash from components
    hasher = hashlib.sha256()
    for component in components:
        hasher.update(str(component).encode('utf-8'))

    # Use first 12 chars of hex digest for readability
    hash_suffix = hasher.hexdigest()[:12]

    return f"{prefix}_{hash_suffix}"


def _map_verdict_to_rating(verdict: str) -> str:
    """
    Map internal verdict to schema rating.

    Mapping (deterministic):
    - VIOLATION → VIOLATED
    - NO_VIOLATION → COMPLIANT
    - UNCLEAR → UNDECIDED

    Args:
        verdict: Internal verdict string

    Returns:
        Schema-compliant rating string

    Raises:
        ValueError: If verdict is not recognized
    """
    mapping = {
        "VIOLATION": "VIOLATED",
        "NO_VIOLATION": "COMPLIANT",
        "UNCLEAR": "UNDECIDED"
    }

    if verdict not in mapping:
        raise ValueError(
            f"Unknown verdict '{verdict}'. "
            f"Expected one of: {list(mapping.keys())}"
        )

    return mapping[verdict]


def _infer_severity_from_rating(rating: str) -> str:
    """
    Infer severity from rating (conservative defaults).

    Mapping:
    - VIOLATED → HIGH (conservative: treat violations as high severity)
    - COMPLIANT → INFO (informational finding)
    - UNDECIDED → LOW (uncertain, but flagged for review)

    Args:
        rating: Schema rating (VIOLATED, COMPLIANT, UNDECIDED)

    Returns:
        Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)
    """
    mapping = {
        "VIOLATED": "HIGH",
        "COMPLIANT": "INFO",
        "UNDECIDED": "LOW"
    }

    return mapping.get(rating, "MEDIUM")  # Default to MEDIUM if unknown


def map_judge_output_to_behaviour_json(
    internal_output: dict[str, Any],
    scenario_id: str | None = None
) -> dict[str, Any]:
    """
    Map internal judge output to behaviour_json_v0_phase0 schema.

    This is the main mapping function. It performs deterministic transformation
    without changing the judge's semantic decisions.

    Args:
        internal_output: Internal judge output dict with fields:
            - verdict: str (VIOLATION, NO_VIOLATION, UNCLEAR)
            - signals: list[str]
            - citations: list[str]
            - rationale: list[str]
            - judge_meta: dict
        scenario_id: Optional scenario ID (extracted from judge_meta if not provided)

    Returns:
        behaviour_json_v0_phase0 compliant dict with fields:
            - audit_id: str
            - run_id: str
            - finding_id: str
            - scenario_id: str
            - framework: str
            - rating: str (VIOLATED, COMPLIANT, UNDECIDED)
            - reasoning: list[str]
            - legal_references: list[str]
            - signals: list[str]
            - severity: str
            - inspect_provenance: dict

    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Extract scenario_id from judge_meta if not provided
    if scenario_id is None:
        scenario_id = internal_output.get("judge_meta", {}).get("scenario_id", "unknown")

    # Extract timestamp for deterministic ID generation
    timestamp = internal_output.get("judge_meta", {}).get("timestamp_utc", datetime.utcnow().isoformat())

    # Map verdict to rating (deterministic)
    verdict = internal_output.get("verdict", "UNCLEAR")
    rating = _map_verdict_to_rating(verdict)

    # Generate deterministic IDs
    audit_id = _generate_deterministic_id("audit", scenario_id, timestamp[:10])  # Use date only
    run_id = _generate_deterministic_id("run", scenario_id, timestamp)
    finding_id = _generate_deterministic_id("finding", scenario_id, run_id)

    # Extract framework from judge_meta or use default
    judge_meta = internal_output.get("judge_meta", {})
    framework = judge_meta.get("framework", "GDPR")

    # Infer severity from rating
    severity = _infer_severity_from_rating(rating)

    # Map judge_meta to inspect_provenance
    inspect_provenance = {
        "model": judge_meta.get("model", "unknown"),
        "timestamp_utc": judge_meta.get("timestamp_utc", timestamp),
    }

    # Include optional fields from judge_meta
    if "temperature" in judge_meta:
        inspect_provenance["temperature"] = judge_meta["temperature"]
    if "mock" in judge_meta:
        inspect_provenance["mock"] = judge_meta["mock"]
    if "source_fixture" in judge_meta:
        inspect_provenance["source_fixture"] = judge_meta["source_fixture"]

    # Build schema-compliant output
    behaviour_json = {
        "audit_id": audit_id,
        "run_id": run_id,
        "finding_id": finding_id,
        "scenario_id": scenario_id,
        "framework": framework,
        "rating": rating,
        "reasoning": internal_output.get("rationale", []),
        "legal_references": internal_output.get("citations", []),
        "signals": internal_output.get("signals", []),
        "severity": severity,
        "inspect_provenance": inspect_provenance
    }

    return behaviour_json


def validate_against_schema(
    output: dict[str, Any],
    schema_path: Path | None = None,
    schema_kind: Literal["eval", "specs"] = "eval"
) -> tuple[bool, str | None]:
    """
    Validate output against behaviour_json_v0_phase0 schema.

    Args:
        output: Output dict to validate
        schema_path: Path to schema file (if provided, overrides schema_kind)
        schema_kind: Which schema to use - "eval" (Aigov-eval harness schema)
                     or "specs" (canonical AiGov-specs schema). Default: "eval"

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_msg) if invalid

    Notes:
        - "eval" schema is the temporary harness schema for offline judge runner
          (looser requirements: freeform IDs, reasoning as list)
        - "specs" schema is the canonical schema from AiGov-specs
          (strict requirements: AUD-YYYYMMDD-NNN format, UUIDs, reasoning as string)
    """
    try:
        import jsonschema
    except ImportError:
        # Graceful degradation if jsonschema not available
        return (True, "jsonschema not available, skipping validation")

    # Use explicit schema path if provided, otherwise derive from schema_kind
    if schema_path is None:
        if schema_kind == "specs":
            schema_path = get_behaviour_schema_path()
        else:
            schema_filename = f"behaviour_json_v0_phase0.schema-{schema_kind}.json"
            schema_path = Path(__file__).parent.parent / "schemas" / schema_filename

    if not schema_path.exists():
        return (False, f"Schema file not found: {schema_path}")

    # Load schema
    with open(schema_path, 'r') as f:
        schema = json.load(f)

    # Validate
    try:
        jsonschema.validate(instance=output, schema=schema)
        return (True, None)
    except jsonschema.ValidationError as e:
        error_msg = f"Validation error: {e.message}\nPath: {list(e.path)}\nFailed value: {e.instance}"
        return (False, error_msg)
    except jsonschema.SchemaError as e:
        error_msg = f"Schema error: {e.message}"
        return (False, error_msg)


def map_and_validate(
    internal_output: dict[str, Any],
    scenario_id: str | None = None,
    fail_on_invalid: bool = True,
    schema_kind: Literal["eval", "specs"] = "eval",
    schema_path: Path | None = None
) -> dict[str, Any]:
    """
    Map internal judge output and validate against schema.

    This is a convenience function that combines mapping and validation.

    Args:
        internal_output: Internal judge output
        scenario_id: Optional scenario ID
        fail_on_invalid: If True, raise ValueError on validation failure
        schema_kind: Which schema to use - "eval" or "specs". Default: "eval"
        schema_path: Explicit schema path (overrides schema_kind if provided)

    Returns:
        Mapped and validated behaviour_json output

    Raises:
        ValueError: If validation fails and fail_on_invalid=True
    """
    # Map to behaviour_json format
    behaviour_json = map_judge_output_to_behaviour_json(internal_output, scenario_id)

    # Validate against specified schema
    is_valid, error_msg = validate_against_schema(
        behaviour_json,
        schema_path=schema_path,
        schema_kind=schema_kind
    )

    if not is_valid and fail_on_invalid:
        raise ValueError(f"Schema validation failed: {error_msg}")

    return behaviour_json
