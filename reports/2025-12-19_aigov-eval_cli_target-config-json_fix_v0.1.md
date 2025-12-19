# AiGov-eval CLI target-config-json Fix Report

**Date**: 2025-12-19

## What Changed
- Hardened `_load_target_config` to return `{}` when missing, validate JSON, and enforce object type.
- Added tests for valid, invalid, and non-object JSON cases.

## Why It Changed
- CLI crashed with `NameError` and lacked validation; HTTP target usage should be reliable and deterministic.

## Repro Command
```bash
python -m aigov_eval.cli run --target http --target-config-json '{"base_url":"http://localhost:8000","chat_path":"/chat"}' --scenario examples/scenarios/pii_disclosure.yaml --out runs/
```

## Files Modified
- `aigov_eval/cli.py`
- `tests/minimal_loop/test_cli_target_config_json.py`
- `reports/2025-12-19_aigov-eval_cli_target-config-json_fix_v0.1.md`

## Self-check
```text
rg -n "_load_target_config" aigov_eval/cli.py
20:def _load_target_config(raw: str | None) -> dict:
91:        config.update(_load_target_config(args.target_config_json))

git rev-parse HEAD
ea4cf65a20be85e87cfd08c4405aac3117fd6ab1
```
