# Aigov-eval - Evaluation & Testing System

> [!WARNING]
> DEPRECATED: This repo is read-only. Canonical repo is https://github.com/Standivarius/AiGov-monorepo
> Mapping doc: https://github.com/Standivarius/AiGov-monorepo/blob/main/docs/migration/LEGACY_REPOS.md
> All evaluation work happens in monorepo.

**AIGov Systematic Testing Framework**

---

## 🎯 Purpose

Aigov-eval provides systematic testing and quality assurance for all AIGov audit components, ensuring:
- **Product Auditability**: Reports defensible in regulatory audits
- **Consistent Performance**: Judge produces stable, repeatable outputs
- **Accurate Legal Reasoning**: AKG/RAG return correct articles and citations
- **Model Selection**: Data-driven LLM selection for Judge role

**NOT primarily for**: LLM selection (that's secondary objective)

---

## 📊 Test Catalog

### Judge Tests (TEST-J01 - J05)
- **TEST-J01**: Output consistency (100 runs, 95%+ target)
- **TEST-J02**: Schema compliance (behaviour_json_v1 format)
- **TEST-J03**: Pattern detection accuracy (known violations)
- **TEST-J04**: Translation fidelity (RO↔EN preservation)
- **TEST-J05**: Edge case handling (ambiguous violations)

### AKG Tests (TEST-A01 - A04)
- **TEST-A01**: Article retrieval precision (correct articles for violation)
- **TEST-A02**: Citation completeness (all relevant articles found)
- **TEST-A03**: Query latency (<500ms target)
- **TEST-A04**: National overlay accuracy (RO Law 190 integration)

### RAG Tests (TEST-R01 - R03)
- **TEST-R01**: Top-5 retrieval relevance (supporting cases)
- **TEST-R02**: EDPB case coverage (known enforcement decisions)
- **TEST-R03**: Query latency (<500ms target)

### Scenario Tests (TEST-S01 - S03)
- **TEST-S01**: Scenario validity (triggers expected violations)
- **TEST-S02**: Transcript quality (realistic LLM behavior)
- **TEST-S03**: Edge case coverage (ambiguous situations)

### Report Tests (TEST-RE01 - RE03)
- **TEST-RE01**: Report completeness (all sections present)
- **TEST-RE02**: Citation accuracy (correct article references)
- **TEST-RE03**: GRC export format (OneTrust/Vanta/VeriifyWise)

### Council Tests (TEST-C01 - C02)
- **TEST-C01**: Multi-model consensus (3/4 agreement threshold)
- **TEST-C02**: Divergence analysis (why models disagree)

---

## 🏗️ Architecture

### Test Harness Components
1. **Test Runner**: Orchestrates test execution
2. **Known Ground Truth**: EDPB enforcement decisions as validation dataset
3. **LLM Council**: Multi-model voting as proxy expert
4. **Metrics Collector**: Performance, accuracy, cost tracking
5. **Results Dashboard**: Pass/fail rates, trend analysis

### Test Methodology
- **Deterministic Validation**: Same input → same output (consistency)
- **EDPB Case Validation**: Real-world enforcement decisions = ground truth
- **Council Consensus**: 3/4 model agreement for ambiguous cases
- **80%+ Detection Rate**: Minimum target for violation identification

---

## 📁 Repository Structure

```
Aigov-eval/
├── README.md (this file)
├── test-catalog.md (living list of all tests)
├── sources/
│   ├── GDPR & AI Cases and Guidance Dataset.pdf (source material)
│   └── Aigov-eval Dataset Design.md (dataset schema specification)
├── golden_set/
│   └── gs_###.json (normalized case items)
├── cases/
│   └── gs_###__<qid>.json (executable test cases)
├── taxonomy/
│   └── signals.json (valid GDPR violation signals)
├── tools/
│   └── import_golden_set.py (dataset importer)
├── tests/
│   ├── judge/
│   ├── akg/
│   ├── rag/
│   ├── scenarios/
│   ├── reports/
│   └── council/
├── harness/
│   ├── runner.py
│   ├── metrics.py
│   └── dashboard.py
├── ground-truth/
│   ├── edpb-cases/ (known violations)
│   └── synthetic-cases/ (edge cases)
└── docs/
    ├── test-methodology.md
    └── metrics-definitions.md
```

---

## 🚀 Usage

### Importing GDPR Dataset

**Step 1**: Place your source PDF in the `sources/` directory:
```
sources/GDPR & AI Cases and Guidance Dataset.pdf
```

**Step 2**: Run the importer:
```bash
# Import all cases from PDF
python tools/import_golden_set.py

# Import specific range (items 1-10)
python tools/import_golden_set.py --start 1 --end 10

# Dry run (preview without writing files)
python tools/import_golden_set.py --dry-run

# Validate existing outputs
python tools/import_golden_set.py --validate
```

**Alternative - Manual JSON Input**:

If PDF parsing doesn't work or you prefer structured input:
```bash
# Create sample template
python tools/import_golden_set.py --create-sample

# Edit sources/sample_input.json with your data

# Import from JSON
python tools/import_golden_set.py --input-json sources/sample_input.json
```

**Output**:
- `golden_set/gs_###.json` - Normalized case items with metadata
- `cases/gs_###__<qid>.json` - Executable test cases (one per question)

**Features**:
- ✅ Automatic GDPR citation resolution (Art. 5(1)(a) → local docs)
- ✅ Taxonomy validation (signals checked against `taxonomy/signals.json`)
- ✅ Missing field detection (flags `needs_human_fill: true`)
- ✅ Stdlib-only runtime (PDF parsing optional dependency)

See `sources/Aigov-eval Dataset Design.md` for complete schema specification.

### Running Tests

```bash
# Run all tests
python harness/runner.py --all

# Run specific test suite
python harness/runner.py --suite judge

# Run single test
python harness/runner.py --test TEST-J01

# Run failed tests only
python harness/runner.py --failed-only

# Run importer tests
pytest tests/test_import_golden_set.py -v
```

### Adding New Test

1. Add to `test-catalog.md`:
```markdown
### TEST-J06: Context Preservation
**Status**: PLANNED
**Priority**: P1
**Description**: Verify Judge maintains context across multi-turn scenarios
**Success Criteria**: 90%+ context accuracy
```

2. Implement in `tests/judge/test_j06_context.py`

3. Run and update status: PLANNED → IMPLEMENTED → VALIDATED

---

## 📋 Test Catalog Status

**Total Tests**: 25  
**Implemented**: 0  
**Planned**: 25  
**Pass Rate**: N/A (not yet run)

See [test-catalog.md](test-catalog.md) for complete list.

---

## 🔗 Links

- **Main Project**: [Aigov-specs](https://github.com/Standivarius/AiGov-specs)
- **Master Plan**: [Master Plan v3](https://github.com/Standivarius/AiGov-specs/blob/main/docs/planning/Master-Plan-v3.md)
- **Notion Dashboard**: Strategic overview & business metrics

---

## 🧪 LLM Council Research

**Candidates**:
- Gemini 2.0 Flash Thinking
- Claude Sonnet 4.5
- GPT-4.5.1
- Mistral Large 3

**Testing Protocol**:
- Same RO transcript → 5 models
- Measure: Translation, pattern detection, article precision, cost, latency

**Research**: Check existing implementations (e.g., Karpathy's llm-council) before building custom

---

## 🎓 Guiding Principles

1. **Evidence Over Opinion**: Use EDPB cases (real violations) as ground truth
2. **Council Over Expert**: LLM consensus cheaper than hiring lawyers
3. **Deterministic First**: Consistency matters more than perfection
4. **Living Catalog**: Tests discovered → added → implemented → validated
5. **Reusable Design**: System applicable to other compliance products


[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Standivarius/Aigov-eval)

---

**Status**: Phase 0 - Structure defined, implementation pending  
**Next Milestone**: Implement Judge consistency tests (Phase 2)  
**Last Updated**: 2025-12-11
