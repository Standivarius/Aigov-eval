# AiGov-eval HTTP Target Schema + BOM Fix Report

**Date**: 2025-12-19

## What Changed
- HTTP target now posts `messages` (role/content list) instead of a single `message`.
- Role normalization maps unknown roles to `user` or `assistant` for TargetLab compatibility.
- Added a Windows-friendly example config and documented file-based CLI usage.
- Config file loading uses UTF-8 BOM-safe decoding for `--target-config-file`.

## Why
- TargetLab /chat expects `messages`; 422 errors reported missing `body.messages`.
- Windows JSON files often include a UTF-8 BOM, which breaks strict JSON parsers.

## Windows Run Commands
```bash
python -m aigov_eval.cli run --scenario examples/scenarios/special_category_leak.yaml --target http --target-config-file examples/target_config_http.json --out runs/ --debug
```

## Acceptance Check Commands
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest tests/minimal_loop -q
```
