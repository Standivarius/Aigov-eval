# AIGov-Eval Plan

## Purpose of this repo
Evaluation harness for audit-style testing of Judge behaviour:
- verdict correctness + repeatability
- signal taxonomy detection (required vs allowed extras)
- observability fields for auditor-defensible evidence

This repo is NOT the product MVP.

## Current status (Phase 0)
- 12 GDPR calibration cases
- v2 expected_outcome supported:
  - required_signals
  - allowed_extra_signals
- Batch runner emits:
  - required_recall_accuracy, allowed_only_accuracy
  - strict/subset accuracy, repeatability metrics
- Reports written under runs/batch_*/batch_report.md

## Phase 1 (next)
Goal: increase coverage and reduce the chance we are overfitting to 12 cases.
1) Expand GDPR case pack to 50–100 cases across categories.
2) Add “failure triage loop”:
   - store failing outputs
   - remediation notes
   - regression re-run list
3) Add richer run artifacts for traceability (raw outputs + config snapshot).

Exit criteria:
- mock batch always green
- live batch stable enough to compare models
- report artifacts sufficient to reproduce failures

## Phase 2 (model bake-off)
Run the same case pack across candidate models with fixed params.
Record:
- accuracy metrics + repeatability + cost/latency
Decide default Judge model for the product.

## Phase 3 (cross-framework)
Generalise via data/config, not code forks:
- new taxonomy + prompt/rubric + case packs for ISO/EU AI Act
- reuse the same batch runner + reporting pipeline
