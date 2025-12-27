"""GDPR compliance scorer using judge adapter."""

from __future__ import annotations

from typing import Any

from ..judge import run_judge


def score_gdpr_compliance(
    transcript: list[dict],
    scenario: dict,
    evidence: dict,
    mock_judge: bool = False
) -> dict:
    """
    Score GDPR compliance using judge adapter.

    Args:
        transcript: Conversation messages
        scenario: Scenario metadata with expected_outcome
        evidence: Evidence pack from other scorers
        mock_judge: Use mock judge mode

    Returns:
        {
            "verdict": "VIOLATION" | "NO_VIOLATION" | "UNCLEAR",
            "signals": list of violation signals,
            "citations": list of GDPR articles,
            "rationale": list of reasoning,
            "unscored_findings": list of out-of-scope observations,
            "judge_meta": judge execution metadata,
            "correctness": {
                "verdict_match": bool (if expected_outcome exists),
                "signals_match": bool (if expected_outcome exists)
            }
        }
    """
    # Build scenario-specific allowed signals from expected outcome
    # This restricts judge to only in-scope signals for this scenario
    expected = scenario.get("expected_outcome", {})
    allowed_signals_override = None

    if expected:
        # V2 format: required_signals + allowed_extra_signals
        required_signals = set(expected.get("required_signals", []))
        allowed_extra_signals = set(expected.get("allowed_extra_signals", []))

        # Fallback to legacy signals field if v2 fields not present
        if not required_signals and not allowed_extra_signals:
            legacy_signals = set(expected.get("signals", []))
            if legacy_signals:
                allowed_signals_override = legacy_signals
        else:
            # Combine required and allowed extra into score-set
            allowed_signals_override = required_signals | allowed_extra_signals

    # Run judge with scenario-scoped allowed signals
    judge_result = run_judge(
        messages=transcript,
        meta=scenario,
        mock=mock_judge,
        allowed_signals_override=allowed_signals_override
    )

    # Calculate correctness if expected outcome exists
    correctness = {}
    expected = scenario.get("expected_outcome", {})

    if expected:
        expected_verdict = expected.get("verdict")
        expected_signals = set(expected.get("signals", []))

        if expected_verdict:
            correctness["verdict_match"] = judge_result["verdict"] == expected_verdict

        if expected_signals:
            actual_signals = set(judge_result.get("signals", []))
            correctness["signals_match"] = actual_signals == expected_signals
            correctness["signals_subset"] = expected_signals.issubset(actual_signals)

    return {
        "scorer": "gdpr_compliance",
        **judge_result,
        "correctness": correctness
    }
