# Judge Tests (Phase 0)

**Purpose**: Systematic validation of Judge component accuracy and reliability.

---

## Schema Namespacing (Important!)

The canonical `behaviour_json_v0_phase0` schema is vendored from AiGov-specs and used for all validation:

- **Vendored path**: `aigov_eval/contracts/behaviour_json_v0_phase0.schema.json`
- **Source**: AiGov-specs `schemas/behaviour_json_v0_phase0.schema.json`
- **Use**: Offline judge runner validation and mapper compliance checks

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
