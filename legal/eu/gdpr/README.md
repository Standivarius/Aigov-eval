# GDPR Legal Documentation

This directory contains reference documentation for GDPR articles and recitals.

## Purpose

The importer (`tools/import_golden_set.py`) generates citation links that point to files in this directory structure:
- `articles/NN.md` - GDPR Articles (e.g., `05.md` for Article 5)
- `recitals/NNN.md` - GDPR Recitals (e.g., `039.md` for Recital 39)

## Current Status

**Status**: Stub files only

This directory currently contains **stub placeholder files** for articles/recitals referenced in the sample golden set.

## Full Documentation

For complete GDPR text and analysis, refer to:
- **Official EUR-Lex**: https://eur-lex.europa.eu/eli/reg/2016/679/oj
- **EDPB Guidelines**: https://edpb.europa.eu/our-work-tools/general-guidance/guidelines-recommendations-best-practices_en
- **AiGov-specs Repository**: (if available) for detailed annotations and interpretations

## Adding New Articles/Recitals

When the importer references a new article or recital:

1. Check the generated case files for citation links
2. Create corresponding stub files if missing
3. (Optional) Populate with full article text and commentary

### Example

If a case references "Art. 32" (Security of processing):

```bash
# Create stub
echo "# GDPR Article 32 - Security of Processing

## Text
[Placeholder - Add article text from EUR-Lex]

## Key Requirements
- Appropriate technical and organizational measures
- Risk-based approach to security
- Regular testing and evaluation

## Related Articles
- Art. 5(1)(f) - Integrity and confidentiality principle
- Art. 25 - Data protection by design and by default

" > articles/32.md
```

## Markdown Anchors

Articles with paragraphs use markdown anchors:
- `articles/05.md#1` - Article 5, paragraph 1
- `articles/05.md#1a` - Article 5(1)(a)

Ensure your markdown has corresponding anchor IDs:
```markdown
## Paragraph 1 {#1}

### (a) Lawfulness, fairness and transparency {#1a}
```

## Automation

Future enhancement: Fetch full text from EUR-Lex API and auto-generate markdown files.
