# Minimal Transcript-First Loop (v0.1)

This repo now includes a minimal evaluation loop that runs transcript-first checks for:
- `PII_DISCLOSURE`
- `SPECIAL_CATEGORY_LEAK`

## Prerequisites
- Python 3.10+
- PyYAML (`pip install pyyaml`) if you run YAML scenarios
- python-dotenv (`pip install python-dotenv`) for .env support (optional)

## Install dependencies into .venv (PowerShell)
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment Variables (LLM Target)
Required:
- `OPENROUTER_API_KEY`

Optional:
- `OPENROUTER_MODEL` (default: `google/gemini-3-flash-preview`)
- `OPENROUTER_BASE_URL` (default: `https://openrouter.ai/api/v1`)
- `OPENROUTER_HTTP_REFERER` (adds `HTTP-Referer` header)
- `OPENROUTER_X_TITLE` (adds `X-Title` header)

Minimal setup:
- Copy `.env.example` to `.env`
- Paste your `OPENROUTER_API_KEY`
- Run a command below

Troubleshooting: API key not detected
- Confirm `.env` is in the repo root (same folder you run the command from).
- Re-run with `--debug` to see whether the `.env` file was found and which keys were loaded.
- If you use a shell session with an exported key, ensure it is set as `OPENROUTER_API_KEY`.

## Run from anywhere
If you're not in the repo root, use `pushd`/`popd`:
```bash
pushd C:\Users\User\OneDrive - Remote-skills\Documents\Projects\AIGov\repos\Aigov-eval
python -m aigov_eval.cli run --scenario examples/scenarios/pii_disclosure.yaml --target scripted --out runs/
popd
```

## Run Scripted Target
Deterministic output with a deliberate leak:

```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure.yaml --target scripted --out runs/
python -m aigov_eval run --scenario examples/scenarios/special_category_leak.yaml --target scripted --out runs/
```

## Run Mock LLM Target (non-leaky)
OpenAI-compatible Chat Completions via OpenRouter:

```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure.yaml --target mock-llm --out runs/
```

## Run Mock LLM Target (leaky positive control)
Deterministic leak mode with profile and threshold control:

```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target mock-llm --leaky --leak-profile pii_basic --leak-after 2 --out runs/
python -m aigov_eval run --scenario examples/scenarios/special_category_leak_positive_control.yaml --target mock-llm --leaky --leak-profile special_category_basic --leak-after 2 --out runs/
```

## Deterministic PASS/FAIL Runs (MVP)
PII non-leaky (expect PASS):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target mock-llm --out runs/
```

PII leaky (expect FAIL):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target mock-llm --leaky --leak-profile pii_basic --leak-after 2 --out runs/
```

Special category non-leaky (expect PASS):
```bash
python -m aigov_eval run --scenario examples/scenarios/special_category_leak_positive_control.yaml --target mock-llm --out runs/
```

Special category leaky (expect FAIL):
```bash
python -m aigov_eval run --scenario examples/scenarios/special_category_leak_positive_control.yaml --target mock-llm --leaky --leak-profile special_category_basic --leak-after 2 --out runs/
```

Note: when a leak occurs, the assistant output includes a final line like:
`<<MOCK_AUDIT>> {"leaked_fields":["email"],"turn_index":3}`
This line contains field names and turn index only, no sensitive values.

## Run HTTP Target (TargetLab local)
Assumes TargetLab is running at `http://localhost:8000` and exposes `POST /chat`.

PII strict (expect PASS):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target http --target-config-json '{"base_url":"http://localhost:8000","leak_mode":"strict","leak_profile":"pii","use_llm":false}' --out runs/
```

PII leaky (expect FAIL):
```bash
python -m aigov_eval run --scenario examples/scenarios/pii_disclosure_positive_control.yaml --target http --target-config-json '{"base_url":"http://localhost:8000","leak_mode":"leaky","leak_profile":"pii","use_llm":false}' --out runs/
```

Special category strict (expect PASS):
```bash
python -m aigov_eval run --scenario examples/scenarios/special_category_leak_positive_control.yaml --target http --target-config-json '{"base_url":"http://localhost:8000","leak_mode":"strict","leak_profile":"special_category","use_llm":false}' --out runs/
```

Special category leaky (expect FAIL):
```bash
python -m aigov_eval run --scenario examples/scenarios/special_category_leak_positive_control.yaml --target http --target-config-json '{"base_url":"http://localhost:8000","leak_mode":"leaky","leak_profile":"special_category","use_llm":false}' --out runs/
```

Unit tests for the HTTP target are stubbed; they monkeypatch the HTTP client so no
TargetLab container is required.

## Outputs
Each run writes:
- `runs/<run_id>/transcript.json`
- `runs/<run_id>/scores.json`
- `runs/<run_id>/evidence_pack.json`
- `runs/<run_id>/run_meta.json`

## Dev Note (AiGov-specs Integration)
This loop expects simple scenario files now, but it is aligned with scenario-card concepts
(`scenario_id`, `framework`, `role`, `auditor_seed`, and `failure_criteria`). The next step
is to point the loader at canonical scenario-card files in AiGov-specs and map their fields
into the `turns` list used by this runner.
