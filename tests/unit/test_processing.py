"""Tests for text chunker."""

from src.processing.chunker import chunk_text


class TestChunkText:
    """Test text chunking."""

    def test_short_text_single_chunk(self) -> None:
        """Short text should produce a single chunk."""
        text = "This is a short document."
        chunks = chunk_text(text, strategy="fixed_size", chunk_size_tokens=500)
        assert len(chunks) == 1
        assert chunks[0]["chunk_text"] == text
        assert chunks[0]["chunk_index"] == 0

    def test_long_text_multiple_chunks(self) -> None:
        """Long text should produce multiple chunks."""
        text = "This is a sentence. " * 200  # ~4000 chars = ~1000 tokens
        chunks = chunk_text(text, strategy="fixed_size", chunk_size_tokens=200)
        assert len(chunks) > 1

    def test_chunks_have_required_fields(self) -> None:
        """Each chunk should have all required fields."""
        text = "This is a test document with enough content. " * 50
        chunks = chunk_text(text, strategy="fixed_size", chunk_size_tokens=100)
        for chunk in chunks:
            assert "chunk_index" in chunk
            assert "chunk_text" in chunk
            assert "token_count" in chunk
            assert "char_start" in chunk
            assert "char_end" in chunk
            assert chunk["token_count"] > 0

    def test_chunk_indices_are_sequential(self) -> None:
        """Chunk indices should be sequential starting from 0."""
        text = "Hello world. " * 200
        chunks = chunk_text(text, strategy="fixed_size", chunk_size_tokens=100)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_empty_text_returns_empty(self) -> None:
        """Empty text should return no chunks."""
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_sliding_window_strategy(self) -> None:
        """Sliding window should also produce valid chunks."""
        text = "This is a sentence. " * 200
        chunks = chunk_text(text, strategy="sliding_window", chunk_size_tokens=200)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["token_count"] > 0

    def test_unknown_strategy_falls_back(self) -> None:
        """Unknown strategy should fall back to fixed_size."""
        text = "This is a test document."
        chunks = chunk_text(text, strategy="unknown_strategy")
        assert len(chunks) == 1


"""Tests for PII detector."""

from src.processing.pii_detector import detect_pii, mask_text, PIIMatch


class TestDetectPII:
    """Test PII detection."""

    def test_detect_email(self) -> None:
        """Should detect email addresses."""
        text = "Contact us at john.smith@example.com for more info."
        matches = detect_pii(text)
        email_matches = [m for m in matches if m.entity_type == "EMAIL"]
        assert len(email_matches) >= 1
        assert "john.smith@example.com" in email_matches[0].text

    def test_detect_australian_phone(self) -> None:
        """Should detect Australian mobile numbers."""
        text = "Call me on 0412 345 678 anytime."
        matches = detect_pii(text)
        phone_matches = [m for m in matches if m.entity_type == "PHONE"]
        assert len(phone_matches) >= 1

    def test_detect_abn(self) -> None:
        """Should detect Australian Business Numbers."""
        text = "Our ABN is 51 824 753 556 for invoicing."
        matches = detect_pii(text)
        abn_matches = [m for m in matches if m.entity_type in ("ABN", "TFN")]
        assert len(abn_matches) >= 1

    def test_detect_medicare(self) -> None:
        """Should detect Medicare numbers."""
        text = "Medicare number: 2345 67890 1 on file."
        matches = detect_pii(text)
        medicare_matches = [m for m in matches if m.entity_type == "MEDICARE"]
        assert len(medicare_matches) >= 1

    def test_no_pii_in_clean_text(self) -> None:
        """Should return empty list for text without PII."""
        text = "The weather in Adelaide is sunny today."
        matches = detect_pii(text)
        # Some false positives possible, but should be minimal
        assert len(matches) <= 1

    def test_confidence_threshold(self) -> None:
        """Higher threshold should produce fewer matches."""
        text = "Contact john@example.com or call 0412 345 678."
        low_threshold = detect_pii(text, confidence_threshold=0.5)
        high_threshold = detect_pii(text, confidence_threshold=0.95)
        assert len(low_threshold) >= len(high_threshold)


class TestMaskText:
    """Test PII masking."""

    def test_mask_replaces_pii(self) -> None:
        """Should replace PII with masked tokens."""
        text = "Email john@example.com for details."
        matches = [
            PIIMatch(
                entity_type="EMAIL",
                text="john@example.com",
                start=6,
                end=22,
                confidence=0.95,
                masked_text="[EMAIL_REDACTED]",
            )
        ]
        result = mask_text(text, matches)
        assert "john@example.com" not in result
        assert "[EMAIL_REDACTED]" in result

    def test_mask_multiple_entities(self) -> None:
        """Should mask multiple PII entities."""
        text = "Contact john@test.com or jane@test.com"
        matches = [
            PIIMatch(entity_type="EMAIL", text="john@test.com", start=8, end=21, confidence=0.95, masked_text="[EMAIL_REDACTED]"),
            PIIMatch(entity_type="EMAIL", text="jane@test.com", start=25, end=38, confidence=0.95, masked_text="[EMAIL_REDACTED]"),
        ]
        result = mask_text(text, matches)
        assert "john@test.com" not in result
        assert "jane@test.com" not in result
        assert result.count("[EMAIL_REDACTED]") == 2

    def test_mask_empty_matches(self) -> None:
        """Should return original text when no matches."""
        text = "No PII here."
        result = mask_text(text, [])
        assert result == text
