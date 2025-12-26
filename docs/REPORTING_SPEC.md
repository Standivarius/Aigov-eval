# REPORTING_SPEC.md (v0)

Goal: every run under `runs/batch_*/` must be reconstructable later (what model, what prompts, what inputs/outputs, what failed).

## Batch folder contract
Each `runs/batch_<timestamp>/` contains:
- `batch_summary.json` (machine-readable single source of truth)
- `batch_report.md` (human-readable)
- `artifacts/` (raw evidence)

## batch_summary.json must include
### batch_meta
- timestamp, git_sha, python_version
- cases_dir, repeats
- mock_judge (bool)
- target (adapter name)
- judge provider config (at minimum: model, base_url/provider, temperature if applicable)

### case_results[]
For each case + repeat:
- scenario_id, case_file
- expected outcome (required signals, allowed extra signals, expected verdict)
- actual: verdict + signals (per repeat)
- modal_signals and modal_verdict
- required_recall_pass + missing_required_signals
- allowed_only_pass + extra_unallowed_signals

### aggregate_metrics
- verdict_accuracy, mean_verdict_repeatability
- signals_strict_accuracy, signals_subset_accuracy, mean_signals_repeatability
- required_recall_accuracy (+ counts)
- allowed_only_accuracy (+ counts)

## artifacts/ (minimum)
Per case-repeat:
- prompt(s) sent to judge/target
- raw model output
- parsed output
- error payloads (if any), with retry count
- latency + token usage if available
