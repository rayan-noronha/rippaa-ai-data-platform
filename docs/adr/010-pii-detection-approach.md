# ADR-010: PII Detection with Presidio and Custom Australian Recognizers

## Status

Accepted

## Date

2026-03-31

## Context

Enterprise documents contain Personally Identifiable Information (PII) that must be detected and masked before storing embeddings. In regulated industries (insurance, financial services, government), PII handling is a legal requirement under the Privacy Act 1988 (Cth) and APRA CPS 234.

PII types we need to detect:
- Standard: names, email addresses, phone numbers, credit card numbers
- Australian-specific: ABN (Australian Business Number), Medicare numbers, TFN (Tax File Number), Australian phone formats

Options considered:

1. **Microsoft Presidio** — Open-source PII detection library with pluggable recognizers
2. **AWS Comprehend** — Managed NLP service with PII detection
3. **spaCy NER only** — Named entity recognition without dedicated PII framework
4. **Custom regex only** — Hand-written patterns for each PII type
5. **Google Cloud DLP** — Managed data loss prevention service

## Decision

We use **Microsoft Presidio** with custom pattern recognizers for Australian PII types, with a **regex fallback** when Presidio's spaCy models aren't available.

## Rationale

### Why Presidio
- Open-source with no per-call cost (unlike Comprehend or DLP)
- Pluggable architecture — we add custom recognizers without modifying the core library
- Supports both pattern-based (regex) and NLP-based (spaCy) detection
- Well-maintained by Microsoft with active community
- Runs locally — no data sent to external APIs during PII scanning

### Custom Australian recognizers
- ABN pattern: `\d{2}\s\d{3}\s\d{3}\s\d{3}` (e.g., "51 824 753 556")
- Medicare: `\d{4}\s\d{5}\s\d{1}` (e.g., "2345 67890 1")
- TFN: `\d{3}\s\d{3}\s\d{3}` (e.g., "123 456 789")
- AU phone: `04\d{2}\s\d{3}\s\d{3}` (e.g., "0412 345 678")
- These patterns are registered as first-class entity types with configurable confidence scores

### Why regex fallback
- Presidio requires spaCy language models which can be large (~500MB)
- In CI or minimal environments, the regex fallback ensures PII detection still works
- Regex catches the most critical patterns (emails, phones, ABNs) with high confidence
- The fallback is transparent — the same `detect_pii()` function works in both modes

### Why not AWS Comprehend
- Comprehend charges per character scanned — at 53 documents with multiple chunks each, costs add up
- Comprehend doesn't natively detect Australian-specific PII (ABN, Medicare, TFN)
- Adds an external API dependency to the processing pipeline
- May be added as an optional enrichment layer in future for name detection improvement

### Detection results
- Our pipeline detected 1,688 PII entities across 53 documents
- Breakdown: 804 persons, 343 phones, 284 emails, 126 ABNs, 126 TFNs, 5 Medicare numbers
- All detected PII is masked before embedding generation
- Full audit trail stored in `pii_detections` table

## Consequences

- PII detection adds ~0.5s per document to processing time
- Masked text (not original) is embedded — embeddings are PII-free
- Original PII text is stored only in the audit table for compliance review
- Confidence threshold (0.7) is configurable — can be tuned per entity type
- False positives are possible (e.g., any 9-digit number matching TFN pattern) — accepted as safer than false negatives

## References

- [Microsoft Presidio](https://microsoft.github.io/presidio/)
- [Privacy Act 1988 (Cth)](https://www.legislation.gov.au/Series/C2004A03712)
- [APRA CPS 234](https://www.apra.gov.au/information-security)
