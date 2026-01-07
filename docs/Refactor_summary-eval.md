# Aigov-eval refactor summary (closure)

## What is “done”
- Batch runner works end-to-end for GDPR Phase0 cases.
- Targets confirmed: scripted, mock-llm, http.
- “True live” run validated with target=mock-llm and OpenRouter key.
- Run artefacts are written under: <out>/batch_<timestamp>/
  - batch_summary.json
  - batch_report.md
  - per-case folders

## Key contract decisions
- Batch output path contract is directory-based (batch_<timestamp> folder).
- batch_meta includes a judge object (provider/model/base_url/usage) derived from first available judge_meta.
- Evidence capture remains lightweight JSON artefacts (no orchestration framework required).

## How to run (fast)
- Live smoke:
  python -m aigov_eval.cli batch-run --cases-dir cases/calibration --repeats 1 --out runs/fast --target mock-llm
- CI baseline:
  python -m aigov_eval.cli batch-run --cases-dir cases/calibration --repeats 1 --out runs/ci --mock-judge --target scripted

## Current status
- pytest passes (expected one skip when OPENROUTER_API_KEY missing).
