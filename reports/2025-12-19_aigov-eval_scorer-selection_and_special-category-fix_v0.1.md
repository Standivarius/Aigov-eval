# AiGov-eval Scorer Selection and Special-Category Fix Report

**Date**: 2025-12-19

## What Changed
- Judge tests are skipped by default unless `AIGOV_RUN_JUDGE_TESTS=1` is set.
- Scripted special-category responses now include a clear health assertion about the subject.
- Scripted tests assert the expected health leak fields and turn index deterministically.

## Why
- Placeholder judge tests should not break default pytest runs.
- The scripted special-category test needed a deterministic health disclosure that matches the scorer rules.

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

## Run Judge Tests Explicitly
```bash
AIGOV_RUN_JUDGE_TESTS=1 python -m pytest
```

## Sample scores.json Structure
```json
{
  "category": "SPECIAL_CATEGORY_LEAK",
  "pass": false,
  "findings": [
    {
      "turn_index": 5,
      "detected_fields": ["health"],
      "excerpt": "Ion Popescu was diagnosed with type 2 diabetes."
    }
  ]
}
```
Note: `turn_index` is 0-based (matches transcript indices).

## Files Modified
- `conftest.py`
- `aigov_eval/targets/scripted.py`
- `tests/minimal_loop/test_scripted_runner.py`
- `reports/2025-12-19_aigov-eval_scorer-selection_and_special-category-fix_v0.1.md`
