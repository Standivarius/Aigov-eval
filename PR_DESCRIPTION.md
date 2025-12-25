# Pull Request: Add v2 expected_outcome format with flexible signal scoring

**Branch:** `claude/gdpr-signal-flexibility-O5Hnx`
**Base:** `main`

**Create PR at:** https://github.com/Standivarius/Aigov-eval/pull/new/claude/gdpr-signal-flexibility-O5Hnx

---

## Summary

This PR upgrades GDPR calibration cases and scoring to support v2 expected_outcome format with flexible signal evaluation:

- **Updated 2 calibration cases** (cal_001, cal_002) to v2 format with `required_signals` and `allowed_extra_signals`
- **Added new per-case metrics**:
  - `required_recall_pass`: Validates all required signals are detected (recall)
  - `allowed_only_pass`: Validates no unallowed extra signals are present (precision)
- **Added aggregate metrics**: `required_recall_accuracy` and `allowed_only_accuracy`
- **Updated reporting**: Both `batch_summary.json` and `batch_report.md` now include v2 metrics
- **Backwards compatible**: Mock judge supports both v1 (`signals`) and v2 (`required_signals`) formats
- **Comprehensive testing**: 5 new unit tests + 1 integration test

## Why

The v1 format treated all extra signals as failures, which penalized AI judges for detecting reasonable related violations (e.g., "unlawful_processing" when evaluating consent violations).

The v2 format enables more nuanced evaluation by:
1. Enforcing detection of **core signals** (required_signals) - ensures judges catch critical violations
2. Allowing **reasonable extras** (allowed_extra_signals) - prevents penalizing thorough analysis
3. Separately tracking **recall** (found all required?) and **precision** (only found allowed signals?)

## Testing

✅ All existing tests pass
✅ New unit tests verify metric computation for all scenarios:
   - All required signals present, only allowed extras → both metrics pass
   - Missing required signal → required_recall_pass fails
   - Unallowed extra signal → allowed_only_pass fails
✅ Integration test confirms v2 metrics appear in batch-run output
✅ Manual verification: `python -m aigov_eval.cli batch-run --mock-judge` shows 100% accuracy on both metrics

## Verification

Run batch calibration to see the new metrics:
```bash
python -m aigov_eval.cli batch-run --cases-dir cases/calibration --repeats 5 --out runs --mock-judge
```

Check the output in `runs/batch_*/batch_summary.json`:
- `aggregate_metrics.required_recall_accuracy`
- `aggregate_metrics.allowed_only_accuracy`
- `case_results[*].metrics.required_recall_pass`
- `case_results[*].metrics.allowed_only_pass`

## Files Changed

1. **cases/calibration/cal_001_lack_of_consent.json** - Updated to v2 format
2. **cases/calibration/cal_002_special_category_data.json** - Updated to v2 format
3. **aigov_eval/batch_runner.py** - Added v2 metric computation and reporting
4. **aigov_eval/judge.py** - Updated mock judge for v1/v2 compatibility
5. **tests/batch_calibration/test_batch_runner.py** - Added comprehensive v2 tests
