"""PII detector and masker — identifies and redacts personal information.

Uses Microsoft Presidio for detection with custom recognizers
for Australian-specific PII types (ABN, Medicare, TFN).

Detection happens before embeddings are generated, ensuring
PII-free text is stored in the vector database.
"""

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Try to import Presidio — fall back to regex-based detection if unavailable
try:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning("Presidio not available — using regex-based PII detection")


@dataclass
class PIIMatch:
    """A detected PII entity."""

    entity_type: str
    text: str
    start: int
    end: int
    confidence: float
    masked_text: str


def create_analyzer() -> "AnalyzerEngine | None":
    """Create a Presidio analyzer with custom Australian recognizers."""
    if not PRESIDIO_AVAILABLE:
        return None

    analyzer = AnalyzerEngine()

    # Australian Business Number (ABN): XX XXX XXX XXX
    abn_pattern = Pattern(
        name="abn_pattern",
        regex=r"\b\d{2}\s\d{3}\s\d{3}\s\d{3}\b",
        score=0.85,
    )
    abn_recognizer = PatternRecognizer(
        supported_entity="AU_ABN",
        patterns=[abn_pattern],
        name="Australian ABN Recognizer",
        supported_language="en",
    )
    analyzer.registry.add_recognizer(abn_recognizer)

    # Australian Medicare Number: XXXX XXXXX X
    medicare_pattern = Pattern(
        name="medicare_pattern",
        regex=r"\b\d{4}\s\d{5}\s\d{1}\b",
        score=0.85,
    )
    medicare_recognizer = PatternRecognizer(
        supported_entity="AU_MEDICARE",
        patterns=[medicare_pattern],
        name="Australian Medicare Recognizer",
        supported_language="en",
    )
    analyzer.registry.add_recognizer(medicare_recognizer)

    # Australian Tax File Number (TFN): XXX XXX XXX
    tfn_pattern = Pattern(
        name="tfn_pattern",
        regex=r"\b\d{3}\s\d{3}\s\d{3}\b",
        score=0.7,
    )
    tfn_recognizer = PatternRecognizer(
        supported_entity="AU_TFN",
        patterns=[tfn_pattern],
        name="Australian TFN Recognizer",
        supported_language="en",
    )
    analyzer.registry.add_recognizer(tfn_recognizer)

    # Australian phone numbers: 04XX XXX XXX
    au_phone_pattern = Pattern(
        name="au_phone_pattern",
        regex=r"\b04\d{2}\s\d{3}\s\d{3}\b",
        score=0.85,
    )
    au_phone_recognizer = PatternRecognizer(
        supported_entity="AU_PHONE",
        patterns=[au_phone_pattern],
        name="Australian Phone Recognizer",
        supported_language="en",
    )
    analyzer.registry.add_recognizer(au_phone_recognizer)

    return analyzer


# Module-level analyzer instance (reused across calls)
_analyzer: "AnalyzerEngine | None" = None
_anonymizer: "AnonymizerEngine | None" = None


def _get_analyzer() -> "AnalyzerEngine | None":
    """Get or create the analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = create_analyzer()
    return _analyzer


def _get_anonymizer() -> "AnonymizerEngine | None":
    """Get or create the anonymizer instance."""
    global _anonymizer
    if _anonymizer is None and PRESIDIO_AVAILABLE:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


def detect_pii(
    text: str,
    confidence_threshold: float = 0.7,
) -> list[PIIMatch]:
    """Detect PII entities in text.

    Uses Presidio if available, falls back to regex-based detection.

    Args:
        text: Text to scan for PII.
        confidence_threshold: Minimum confidence to consider a detection.

    Returns:
        List of PIIMatch objects for each detected entity.
    """
    analyzer = _get_analyzer()

    if analyzer is not None:
        return _detect_with_presidio(text, analyzer, confidence_threshold)
    else:
        return _detect_with_regex(text, confidence_threshold)


def _detect_with_presidio(
    text: str,
    analyzer: "AnalyzerEngine",
    confidence_threshold: float,
) -> list[PIIMatch]:
    """Detect PII using Presidio analyzer."""
    entities_to_detect = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "AU_ABN",
        "AU_MEDICARE",
        "AU_TFN",
        "AU_PHONE",
        "CREDIT_CARD",
        "URL",
    ]

    results = analyzer.analyze(
        text=text,
        entities=entities_to_detect,
        language="en",
    )

    matches = []
    for result in results:
        if result.score >= confidence_threshold:
            original_text = text[result.start : result.end]
            masked = _mask_entity(result.entity_type, original_text)
            matches.append(
                PIIMatch(
                    entity_type=_normalize_entity_type(result.entity_type),
                    text=original_text,
                    start=result.start,
                    end=result.end,
                    confidence=result.score,
                    masked_text=masked,
                )
            )

    logger.info("PII detection complete (Presidio)", entities_found=len(matches))
    return matches


def _detect_with_regex(
    text: str,
    confidence_threshold: float,
) -> list[PIIMatch]:
    """Fallback PII detection using regex patterns.

    Less accurate than Presidio but works without spaCy models.
    """
    matches = []

    patterns = [
        # Email addresses
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "EMAIL", 0.95),
        # Australian phone numbers
        (r"\b04\d{2}\s?\d{3}\s?\d{3}\b", "PHONE", 0.85),
        # Landline with area code
        (r"\b08\s?\d{4}\s?\d{4}\b", "PHONE", 0.80),
        # Australian Business Number
        (r"\b\d{2}\s\d{3}\s\d{3}\s\d{3}\b", "ABN", 0.85),
        # Medicare number
        (r"\b\d{4}\s\d{5}\s\d{1}\b", "MEDICARE", 0.85),
        # Tax File Number
        (r"\b\d{3}\s\d{3}\s\d{3}\b", "ABN", 0.60),  # Lower confidence — could be TFN or other number
        # Credit card (basic pattern)
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "CREDIT_CARD", 0.80),
    ]

    for pattern, entity_type, confidence in patterns:
        if confidence < confidence_threshold:
            continue
        for match in re.finditer(pattern, text):
            original_text = match.group()
            masked = _mask_entity(entity_type, original_text)
            matches.append(
                PIIMatch(
                    entity_type=entity_type,
                    text=original_text,
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                    masked_text=masked,
                )
            )

    logger.info("PII detection complete (regex fallback)", entities_found=len(matches))
    return matches


def mask_text(text: str, pii_matches: list[PIIMatch]) -> str:
    """Replace all detected PII in text with masked versions.

    Processes matches in reverse order (by position) to preserve
    character offsets as replacements change string length.

    Args:
        text: Original text containing PII.
        pii_matches: List of detected PII matches.

    Returns:
        Text with all PII replaced by masked tokens.
    """
    if not pii_matches:
        return text

    # Sort by start position in reverse to preserve offsets
    sorted_matches = sorted(pii_matches, key=lambda m: m.start, reverse=True)

    masked_text = text
    for match in sorted_matches:
        masked_text = masked_text[: match.start] + match.masked_text + masked_text[match.end :]

    return masked_text


def _mask_entity(entity_type: str, original_text: str) -> str:
    """Generate a masked replacement for a PII entity."""
    mask_map = {
        "EMAIL": "[EMAIL_REDACTED]",
        "PHONE": "[PHONE_REDACTED]",
        "PERSON": "[PERSON_REDACTED]",
        "ABN": "[ABN_REDACTED]",
        "MEDICARE": "[MEDICARE_REDACTED]",
        "AU_ABN": "[ABN_REDACTED]",
        "AU_MEDICARE": "[MEDICARE_REDACTED]",
        "AU_TFN": "[TFN_REDACTED]",
        "AU_PHONE": "[PHONE_REDACTED]",
        "CREDIT_CARD": "[CREDIT_CARD_REDACTED]",
        "URL": "[URL_REDACTED]",
        "EMAIL_ADDRESS": "[EMAIL_REDACTED]",
        "PHONE_NUMBER": "[PHONE_REDACTED]",
    }
    return mask_map.get(entity_type, f"[{entity_type}_REDACTED]")


def _normalize_entity_type(entity_type: str) -> str:
    """Normalize Presidio entity types to our standard types."""
    normalize_map = {
        "EMAIL_ADDRESS": "EMAIL",
        "PHONE_NUMBER": "PHONE",
        "AU_ABN": "ABN",
        "AU_MEDICARE": "MEDICARE",
        "AU_TFN": "TFN",
        "AU_PHONE": "PHONE",
    }
    return normalize_map.get(entity_type, entity_type)
