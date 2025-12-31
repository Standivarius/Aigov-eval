# Judge Tests (Phase 0)

**Purpose**: Systematic validation of Judge component accuracy and reliability.

---

## Schema Namespacing (Important!)

There are **two different** `behaviour_json_v0_phase0` schemas:

### 1. **eval schema** (`behaviour_json_v0_phase0.schema-eval.json`)
- **Source**: Defined in this repo (Aigov-eval)
- **Purpose**: Temporary harness schema for offline judge runner
- **Requirements**: Looser validation
  - Freeform IDs (e.g., `audit_f41e75ab3a65`)
  - `reasoning` as list of strings
  - `inspect_provenance` requires `model` + `timestamp_utc`
- **Use**: Offline judge runner, development testing

### 2. **specs schema** (`behaviour_json_v0_phase0.schema-specs.json`)
- **Source**: Canonical schema from AiGov-specs repo
- **Purpose**: Production contract for real judge outputs
- **Requirements**: Strict validation
  - IDs in `AUD-YYYYMMDD-NNN` format
  - UUIDs for certain fields
  - `reasoning` as single string
  - `inspect_provenance` requires `log_file`, `sample_id`, `epoch`
- **Use**: Real judge implementation, production systems

**Why the split?**
The eval schema lets us test the harness and mapper logic without blocking on strict ID formats and provenance fields that only make sense in production. The specs schema is the ultimate target for real judge implementations.

**No shadow contract**: Tests are explicit about which schema they validate against.

---

## Test Coverage

### TEST-J01: Output Consistency
**Goal**: Same transcript → same violations (95%+ consistency)  
**Status**: ⏳ Pending  
**File**: `test_j01_consistency.py`

### TEST-J02: Schema Compliance
**Goal**: All outputs validate against behaviour_json_v0_phase0 schema (100%)  
**Status**: ⏳ Pending  
**File**: `test_j02_schema.py`

### TEST-J03: Pattern Detection Accuracy
**Goal**: Judge detects violations in MOCK_LOG (80%+ precision & recall)  
**Status**: ⏳ Pending  
**File**: `test_j03_accuracy.py`

---

## Running Tests

```bash
# Run all Judge tests
pytest tests/judge/ -v

# Run specific test
pytest tests/judge/test_j01_consistency.py -v

# Generate report
pytest tests/judge/ --html=report.html
```

---

## Success Criteria (Phase 0)

✅ TEST-J01: 95%+ consistency across 5 runs  
✅ TEST-J02: 100% schema compliance  
✅ TEST-J03: 80%+ detection accuracy  

**GO/NO-GO**: All 3 tests pass → Judge validated for Phase 1
