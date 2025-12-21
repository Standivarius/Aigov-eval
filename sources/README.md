# Sources Directory

This directory contains source materials for the Aigov-eval dataset.

## Required Files

### GDPR & AI Cases and Guidance Dataset.pdf

**Status**: To be added

This PDF contains the GDPR & AI cases and guidance that will be converted into executable eval artifacts.

**Note**: The PDF file is not included in the repository. Place your PDF file here with the exact name:
```
GDPR & AI Cases and Guidance Dataset.pdf
```

Once the PDF is in place, run the importer:
```bash
python tools/import_golden_set.py
```

## Alternative: Manual JSON Input

If you prefer to skip PDF parsing or if the PDF parser doesn't work well with your document format, you can create a structured JSON file instead.

Generate a sample template:
```bash
python tools/import_golden_set.py --create-sample
```

This creates `sources/sample_input.json` which you can edit with your case data, then import:
```bash
python tools/import_golden_set.py --input-json sources/sample_input.json
```

## File Formats

See `Aigov-eval Dataset Design.md` for complete schema specifications and examples.
