# AiGov-eval Positive-Control Mock Target (Leaky) Report

**Date**: 2025-12-19

## What Changed
- Added deterministic leaky mode to the `mock-llm` target with `--leak-profile` and `--leak-after` controls.
- Appends a `<<MOCK_AUDIT>>` line after a leak and parses it into the evidence pack.
- Updated scorers to include `detected_fields`, `turn_index`, and a short `excerpt` in findings.
- Added positive-control scenarios for PII and special-category leakage.
- Added tests covering non-leaky PASS and leaky FAIL behavior with evidence pack audit parsing.
- Updated README with non-leaky vs leaky usage and positive-control commands.

## How to Run Positive Controls
PII positive control (expect FAIL when leaky, PASS when non-leaky):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target mock-llm --out runs/
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target mock-llm --leaky --leak-profile pii_basic --leak-after 2 --out runs/
```

Special-category positive control (expect FAIL when leaky):
```bash
python -m aigov_eval run --scenario examples/scenarios/special_category_leak_positive_control.yaml --target mock-llm --leaky --leak-profile special_category_basic --leak-after 2 --out runs/
```

## Expected Outcome
- Non-leaky: PASS with no findings.
- Leaky: FAIL with findings; look in `runs/<id>/scores.json` and `runs/<id>/evidence_pack.json`.
- The `<<MOCK_AUDIT>>` line includes only field names and turn index, no sensitive values.
