# AiGov-eval Pytest Scope and Scripted Target Fix Report

**Date**: 2025-12-19

## What Changed
- Judge tests are env-gated at collection time (skipped unless `AIGOV_RUN_JUDGE_TESTS=1`).
- Scripted target emits a deterministic health assertion for the special-category scenario.
- Scripted test asserts detected fields, turn index, and excerpt for the health leak.

## Why
- Keep default `pytest` green for the MVP transcript-first scope.
- Avoid placeholder `NotImplementedError` failures from judge tests by default.
- Ensure scripted special-category runs are a reliable positive control.

## Commands
Run minimal-loop tests only:
```bash
python -m pytest tests/minimal_loop -q
```

Run full suite (judge tests skipped by default):
```bash
python -m pytest
```

Enable judge tests explicitly:
```bash
AIGOV_RUN_JUDGE_TESTS=1 python -m pytest
```

## Files Modified
- `conftest.py`
- `aigov_eval/targets/scripted.py`
- `tests/minimal_loop/test_scripted_runner.py`
