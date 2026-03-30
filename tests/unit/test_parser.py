"""Tests for document parser."""

import pytest

from src.processing.parser import parse_document, ParseError


class TestParseText:
    """Test plain text parsing."""

    def test_parse_simple_text(self) -> None:
        """Should return text content as-is."""
        content = "This is a simple document about insurance policies."
        result = parse_document(content, "txt", "test.txt")
        assert result == content

    def test_parse_multiline_text(self) -> None:
        """Should preserve multiline content."""
        content = "Line one\nLine two\nLine three"
        result = parse_document(content, "txt", "test.txt")
        assert "Line one" in result
        assert "Line three" in result

    def test_parse_bytes_content(self) -> None:
        """Should handle bytes input by decoding to string."""
        content = b"This is bytes content"
        result = parse_document(content, "txt", "test.txt")
        assert result == "This is bytes content"

    def test_empty_content_raises_error(self) -> None:
        """Should raise ParseError for empty content."""
        with pytest.raises(ParseError):
            parse_document("", "txt", "empty.txt")

    def test_whitespace_only_raises_error(self) -> None:
        """Should raise ParseError for whitespace-only content."""
        with pytest.raises(ParseError):
            parse_document("   \n\n  ", "txt", "whitespace.txt")

    def test_unsupported_file_type_raises_error(self) -> None:
        """Should raise ParseError for unsupported file types."""
        with pytest.raises(ParseError, match="Unsupported file type"):
            parse_document("content", "xlsx", "test.xlsx")


class TestParseCSV:
    """Test CSV parsing."""

    def test_parse_valid_csv(self) -> None:
        """Should convert CSV rows to readable text."""
        content = "name,age,city\nAlice,30,Adelaide\nBob,25,Melbourne"
        result = parse_document(content, "csv", "test.csv")
        assert "name: Alice" in result
        assert "age: 30" in result
        assert "city: Adelaide" in result

    def test_parse_csv_with_missing_values(self) -> None:
        """Should skip empty values in rows."""
        content = "name,age,city\nAlice,,Adelaide\nBob,25,"
        result = parse_document(content, "csv", "test.csv")
        assert "name: Alice" in result
        assert "city: Adelaide" in result

    def test_parse_malformed_csv(self) -> None:
        """Should handle malformed CSV without crashing."""
        content = "col1,col2\nval1,val2,extra\nval3"
        result = parse_document(content, "csv", "malformed.csv")
        assert len(result) > 0


class TestParseJSON:
    """Test JSON parsing."""

    def test_parse_simple_json(self) -> None:
        """Should extract key-value pairs from JSON."""
        content = '{"name": "Alice", "role": "Engineer"}'
        result = parse_document(content, "json", "test.json")
        assert "name: Alice" in result
        assert "role: Engineer" in result

    def test_parse_nested_json(self) -> None:
        """Should handle nested JSON structures."""
        content = '{"person": {"name": "Bob", "age": 30}}'
        result = parse_document(content, "json", "test.json")
        assert "person.name: Bob" in result
        assert "person.age: 30" in result

    def test_parse_json_with_arrays(self) -> None:
        """Should handle JSON arrays."""
        content = '{"items": ["apple", "banana"]}'
        result = parse_document(content, "json", "test.json")
        assert "apple" in result
        assert "banana" in result

    def test_invalid_json_raises_error(self) -> None:
        """Should raise ParseError for invalid JSON."""
        with pytest.raises(ParseError, match="Invalid JSON"):
            parse_document("{invalid json", "json", "bad.json")
