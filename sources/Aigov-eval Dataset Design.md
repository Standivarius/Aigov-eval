# Aigov-eval Dataset Design Specification

## Overview

This document defines the structure and schema for GDPR & AI evaluation cases imported from external datasets.

## Directory Structure

```
Aigov-eval/
├── sources/
│   ├── GDPR & AI Cases and Guidance Dataset.pdf  # Source material (DO NOT RENAME)
│   └── Aigov-eval Dataset Design.md               # This file
├── golden_set/
│   └── gs_###.json                                # Normalized golden set items
├── cases/
│   └── gs_###__<qid>.json                         # Executable test cases
├── taxonomy/
│   └── signals.json                               # Valid GDPR violation signals
└── tools/
    └── import_golden_set.py                       # Conversion script
```

## File Naming Conventions

### Golden Set Files
- Format: `gs_###.json` where `###` is a zero-padded 3-digit number (001, 002, etc.)
- Each file contains one normalized case item from the source dataset

### Executable Case Files
- Format: `gs_###__<qid>.json` where:
  - `###` is the golden set item number (matches parent gs_###.json)
  - `<qid>` is a question identifier (e.g., q1, q2, or a slugified question title)
- One case file per question in the golden set item

## Schema Definitions

### Golden Set Item Schema (`golden_set/gs_###.json`)

```json
{
  "item_id": "gs_001",
  "source": "GDPR & AI Cases and Guidance Dataset.pdf",
  "metadata": {
    "authority": "EDPB | DPA-RO | ICO | CNIL | etc.",
    "jurisdiction": "EU | RO | UK | FR | etc.",
    "date": "YYYY-MM-DD",
    "source_url": "https://...",
    "imported_at": "ISO-8601 timestamp",
    "needs_human_fill": false
  },
  "case_description": "Full text description of the case or scenario",
  "questions": [
    {
      "question_id": "q1",
      "question_text": "The actual question text",
      "expected_verdict": "VIOLATION | NO_VIOLATION | UNCLEAR",
      "expected_signals": [
        "lack_of_consent",
        "inadequate_transparency",
        "excessive_data_collection"
      ],
      "gdpr_citations": [
        "Art. 5(1)(a)",
        "Art. 6",
        "Recital 39"
      ],
      "rationale": [
        "First reason bullet point",
        "Second reason bullet point"
      ]
    }
  ],
  "notes": "Any additional context or warnings"
}
```

### Executable Case Schema (`cases/gs_###__<qid>.json`)

This schema extends the existing scenario format used by the eval runner (see `loader.py`):

```json
{
  "scenario_id": "gs_001__q1",
  "title": "Short descriptive title",
  "category": "GDPR_COMPLIANCE",
  "framework": "GDPR",
  "golden_set_ref": "gs_001",
  "question_id": "q1",
  "metadata": {
    "authority": "EDPB",
    "jurisdiction": "EU",
    "date": "2024-03-15",
    "source_url": "https://...",
    "imported_from": "GDPR & AI Cases and Guidance Dataset.pdf"
  },
  "role": "AI auditor evaluating GDPR compliance",
  "auditor_seed": "You are an AI governance auditor. Evaluate this scenario for GDPR compliance.",
  "turns": [
    {
      "role": "user",
      "content": "Case description and context here..."
    },
    {
      "role": "user",
      "content": "The actual question being asked"
    }
  ],
  "expected_outcome": {
    "verdict": "VIOLATION | NO_VIOLATION | UNCLEAR",
    "signals": [
      "lack_of_consent",
      "inadequate_transparency"
    ],
    "gdpr_citations": [
      "Art. 5(1)(a)",
      "Art. 6"
    ],
    "gdpr_citation_links": [
      "legal/eu/gdpr/articles/05.md#1a",
      "legal/eu/gdpr/articles/06.md"
    ],
    "rationale": [
      "Reason 1",
      "Reason 2"
    ]
  },
  "failure_criteria": "System fails if it does not identify the expected GDPR violations",
  "needs_human_fill": false
}
```

## GDPR Citation Resolver

The importer includes a citation resolver that maps GDPR article/recital references to local documentation paths:

### Citation Format Examples
- `Art. 5(1)(a)` → `legal/eu/gdpr/articles/05.md#1a`
- `Article 6` → `legal/eu/gdpr/articles/06.md`
- `Art. 32(1)` → `legal/eu/gdpr/articles/32.md#1`
- `Recital 39` → `legal/eu/gdpr/recitals/039.md`

### Resolver Logic
1. Parse citation text (article number, paragraph, subparagraph)
2. Normalize to zero-padded format
3. Generate repo-relative path
4. No external network calls required

## Taxonomy: GDPR Violation Signals

The `taxonomy/signals.json` file defines valid violation signals that can be referenced in cases:

```json
{
  "version": "1.0.0",
  "signals": [
    {
      "id": "lack_of_consent",
      "title": "Lack of Valid Consent",
      "gdpr_ref": ["Art. 6", "Art. 7"]
    },
    {
      "id": "inadequate_transparency",
      "title": "Inadequate Transparency",
      "gdpr_ref": ["Art. 5(1)(a)", "Art. 12", "Art. 13", "Art. 14"]
    },
    {
      "id": "excessive_data_collection",
      "title": "Excessive Data Collection",
      "gdpr_ref": ["Art. 5(1)(c)"]
    },
    {
      "id": "purpose_limitation_breach",
      "title": "Purpose Limitation Breach",
      "gdpr_ref": ["Art. 5(1)(b)"]
    },
    {
      "id": "inadequate_security",
      "title": "Inadequate Security Measures",
      "gdpr_ref": ["Art. 32"]
    },
    {
      "id": "unlawful_processing",
      "title": "Unlawful Processing",
      "gdpr_ref": ["Art. 6"]
    },
    {
      "id": "rights_violation",
      "title": "Data Subject Rights Violation",
      "gdpr_ref": ["Art. 15", "Art. 16", "Art. 17", "Art. 18", "Art. 20", "Art. 21"]
    },
    {
      "id": "missing_dpia",
      "title": "Missing Data Protection Impact Assessment",
      "gdpr_ref": ["Art. 35"]
    },
    {
      "id": "inadequate_dpo",
      "title": "Inadequate DPO Designation",
      "gdpr_ref": ["Art. 37", "Art. 38", "Art. 39"]
    },
    {
      "id": "breach_notification_failure",
      "title": "Breach Notification Failure",
      "gdpr_ref": ["Art. 33", "Art. 34"]
    },
    {
      "id": "international_transfer_violation",
      "title": "Unlawful International Data Transfer",
      "gdpr_ref": ["Art. 44", "Art. 45", "Art. 46"]
    },
    {
      "id": "profiling_without_safeguards",
      "title": "Automated Decision-Making/Profiling Without Safeguards",
      "gdpr_ref": ["Art. 22"]
    },
    {
      "id": "special_category_violation",
      "title": "Unlawful Processing of Special Categories of Data",
      "gdpr_ref": ["Art. 9"]
    },
    {
      "id": "children_data_violation",
      "title": "Inadequate Protection for Children's Data",
      "gdpr_ref": ["Art. 8"]
    }
  ]
}
```

## Importer Behavior

### Input Processing
1. Parse PDF: Extract case items with metadata, questions, and expected outcomes
2. Validate fields: Check for required fields (authority, jurisdiction, question text)
3. Flag missing data: Set `needs_human_fill: true` if critical fields are missing

### Output Generation
1. Create `golden_set/gs_###.json` for each case item
2. For each question in the item, create `cases/gs_###__<qid>.json`
3. Resolve GDPR citations to local paths
4. Validate signals against taxonomy (or flag for review)

### Error Handling
- Missing fields → Set to `null`, add `needs_human_fill: true`
- Unknown signals → Include with warning, add `needs_human_fill: true`
- Invalid citations → Include raw text, add `needs_human_fill: true`

## Testing Requirements

### Smoke Tests
1. **Import Test**: Run importer on PDF, verify output files exist
2. **Schema Validation**: Load generated JSON, validate against schema
3. **Loader Compatibility**: Use `aigov_eval.loader.load_scenario()` on generated cases
4. **Taxonomy Enforcement**: Verify all signals are in taxonomy or flagged

### Test Data
- Use first 3 items from PDF as test subset
- Validate JSON structure, field presence, data types
- No external dependencies (pyyaml/fastapi/pydantic) in CI

## Usage

### Running the Importer

```bash
# Import all cases from PDF
python tools/import_golden_set.py

# Import specific range (items 1-10)
python tools/import_golden_set.py --start 1 --end 10

# Dry run (show what would be generated)
python tools/import_golden_set.py --dry-run

# Validate existing outputs
python tools/import_golden_set.py --validate
```

### Adding More Sources

1. Place new PDF in `sources/` directory
2. Update importer or create new importer script
3. Follow same naming conventions (`gs_###` for GDPR sources)
4. Use different prefixes for other frameworks (e.g., `ccpa_###`, `aippa_###`)

## Future Extensions

- Support for multi-turn scenarios (currently 1-2 turn patterns)
- Integration with AIGov-specs GDPR documentation repository
- Automated validation against live EDPB database
- Multi-language support (RO, FR, DE translations)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-21
