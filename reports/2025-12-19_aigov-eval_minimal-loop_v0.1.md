# AiGov Eval Minimal Loop v0.1 Report

**Date**: 2025-12-19

## What I Added
- `aigov_eval/` package with loader, runner, scorers, targets, evidence pack builder, and CLI.
- Two example scenarios under `examples/scenarios/` for PII disclosure and special-category leak.
- Minimal pytest coverage for scripted runs and scorer detection.
- `README_MINIMAL_LOOP.md` with usage and environment setup guidance.
- This report under `reports/`.

## Why
The goal was to establish a transcript-first evaluation loop that can run the two most
urgent categories with explainable, heuristic scoring and reproducible scripted targets.
This creates a stable baseline for CI while still supporting LLM-backed runs.

## How to Run
Scripted target (deterministic):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure.yaml --target scripted --out runs/
python -m aigov_eval run --scenario examples/scenarios/special_category_leak.yaml --target scripted --out runs/
```

LLM target (OpenAI-compatible via OpenRouter):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure.yaml --target mock-llm --out runs/
```

Enable leaky mode (telemetry only):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure.yaml --target mock-llm --leaky --out runs/
```

## Example Output (Short)
```
Run 20251219T010101Z_ab12cd34 complete. Outputs in runs/20251219T010101Z_ab12cd34
```

Outputs per run:
- `transcript.json`
- `scores.json`
- `evidence_pack.json`
- `run_meta.json`

## Next Steps
- Expand scenario coverage and map AiGov-specs scenario cards into the loader.
- Add rule-based false-positive suppression (e.g., test data allowlists).
- Add structured severity calibration per risk taxonomy.
