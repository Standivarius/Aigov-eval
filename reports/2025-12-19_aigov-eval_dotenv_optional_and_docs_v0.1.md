# AiGov-eval Optional dotenv + CLI Docs Report

**Date**: 2025-12-19

## What Changed
- Made `python-dotenv` optional; CLI now warns and continues if missing.
- Added `requirements.txt` with runtime dependencies.
- Documented dependency install steps and "run from anywhere" CLI pattern.

## Why It Changed
- HTTP-target runs should not fail when optional `.env` support isn't installed.
- Fresh installs need a single dependency file for required runtime packages.

## Repro Commands (Install + Run HTTP Target)
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m aigov_eval.cli run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target http --target-config-json '{"base_url":"http://localhost:8000","leak_mode":"strict","leak_profile":"pii","use_llm":false}' --out runs/
```

## Files Modified
- `aigov_eval/env.py`
- `requirements.txt`
- `README_DEV.md`
- `README_MINIMAL_LOOP.md`
- `reports/2025-12-19_aigov-eval_dotenv_optional_and_docs_v0.1.md`
