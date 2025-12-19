# AiGov-eval YAML deps + target-config-file Report

**Date**: 2025-12-19

## What Changed + Why
- Added PyYAML to runtime requirements so YAML scenarios work in fresh venv installs.
- Added `--target-config-file` and documented PowerShell-safe usage to avoid inline JSON quoting errors.
- Updated dev deps to include runtime requirements and ensured dotenv remains optional in tests.

## Install Commands
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Commands to Run
Tests:
```bash
python -m pytest tests/minimal_loop -q
```
Output summary:
```
17 passed in 0.31s
```

HTTP target (file-based config):
```bash
python -m aigov_eval.cli run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target http --target-config-file target_config_http.json --out runs/
```

## Files Modified
- `requirements.txt`
- `requirements-dev.txt`
- `aigov_eval/cli.py`
- `tests/minimal_loop/test_cli_env_loading.py`
- `tests/minimal_loop/test_cli_target_config_json.py`
- `README_MINIMAL_LOOP.md`
- `reports/2025-12-19_aigov-eval_yaml-deps_and_target-config-file_v0.1.md`
