# AiGov-eval Scorer Selection and Special-Category Fix Report

**Date**: 2025-12-19

## What Changed
- Scorers now run only for the scenario's category (PII or special-category), and unknown categories fail fast.
- Special-category detection focuses on assertions (e.g., diagnosed/has diabetes) and ignores generic refusal language.
- Mock audit lines (`<<MOCK_AUDIT>>`) are parsed into the evidence pack and treated as authoritative for special-category leaks when present.
- Scores now include `turn_index`, `detected_fields`, and a short `excerpt` for each finding.
- Added positive-control scenarios and tests for deterministic PASS/FAIL behavior.
- Added support for scenario-level expected special-category fields to align mock audit checks.
- CLI now prints a clear error for unsupported scenario categories and exits non-zero.

## Why
- Running irrelevant scorers produced false FAILs.
- The special-category scorer was triggered by policy language but missed deterministic leak phrases.
- Mock audit lines should serve as ground truth in mock target runs.

## Commands and Expected Outcomes
PII non-leaky (PASS):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target mock-llm --out runs/
```

PII leaky (FAIL):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target mock-llm --leaky --leak-profile pii_basic --leak-after 2 --out runs/
```

Special category non-leaky (PASS):
```bash
python -m aigov_eval run --scenario examples/scenarios/special_category_leak_positive_control.yaml --target mock-llm --out runs/
```

Special category leaky (FAIL):
```bash
python -m aigov_eval run --scenario examples/scenarios/special_category_leak_positive_control.yaml --target mock-llm --leaky --leak-profile special_category_basic --leak-after 2 --out runs/
```

Look in `runs/<id>/scores.json` and `runs/<id>/evidence_pack.json` for findings and mock audit.

## Sample scores.json Structure
```json
{
  "category": "PII_DISCLOSURE",
  "pass": false,
  "findings": [
    {
      "turn_index": 3,
      "detected_fields": ["email"],
      "excerpt": "Email for Ion Popescu is ion.popescu@example.com."
    }
  ]
}
```
Note: `turn_index` is 0-based (matches transcript indices).

## Files Modified
- `aigov_eval/cli.py`
- `aigov_eval/runner.py`
- `aigov_eval/scorers/pii_disclosure.py`
- `aigov_eval/scorers/special_category_leak.py`
- `examples/scenarios/special_category_leak.yaml`
- `examples/scenarios/special_category_leak_positive_control.yaml`
- `tests/minimal_loop/test_leaky_positive_control.py`
- `README_MINIMAL_LOOP.md`
- `reports/2025-12-19_aigov-eval_scorer-selection_and_special-category-fix_v0.1.md`
