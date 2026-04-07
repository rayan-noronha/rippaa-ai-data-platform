"""Document parser — extracts text content from various file formats.

Handles TXT, CSV, and JSON files. Designed to handle malformed files
gracefully without crashing the pipeline.
"""

import csv
import io
import json

import structlog

logger = structlog.get_logger(__name__)


class ParseError(Exception):
    """Raised when a document cannot be parsed."""

    pass


def parse_document(content: str | bytes, file_type: str, filename: str) -> str:
    """Parse a document and extract its text content.

    Args:
        content: Raw file content as string or bytes.
        file_type: File format (txt, csv, json, csv_raw).
        filename: Original filename for logging.

    Returns:
        Extracted text content as a single string.

    Raises:
        ParseError: If the document cannot be parsed.
    """
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = content.decode("latin-1")
            except Exception as e:
                raise ParseError(f"Cannot decode file {filename}: {e}") from e

    parser_map = {
        "txt": _parse_text,
        "csv": _parse_csv,
        "csv_raw": _parse_csv,
        "json": _parse_json,
    }

    parser = parser_map.get(file_type)
    if parser is None:
        raise ParseError(f"Unsupported file type: {file_type} for {filename}")

    try:
        text = parser(content, filename)
        if not text or not text.strip():
            raise ParseError(f"No text content extracted from {filename}")
        logger.info(
            "Document parsed",
            filename=filename,
            file_type=file_type,
            text_length=len(text),
        )
        return text.strip()
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Failed to parse {filename} ({file_type}): {e}") from e


def _parse_text(content: str, filename: str) -> str:
    """Parse plain text files — return content as-is."""
    return content


def _parse_csv(content: str, filename: str) -> str:
    """Parse CSV files into readable text.

    Converts each row into a key-value format:
    'column1: value1 | column2: value2 | ...'

    Handles malformed CSVs gracefully — skips bad rows
    instead of crashing.
    """
    lines = []
    try:
        reader = csv.DictReader(io.StringIO(content))
        if reader.fieldnames is None:
            raise ParseError(f"CSV has no headers: {filename}")

        row_count = 0
        error_count = 0
        for row in reader:
            try:
                # Build readable text from row
                parts = []
                for key, value in row.items():
                    if key and value and str(value).strip():
                        parts.append(f"{key}: {value.strip()}")
                if parts:
                    lines.append(" | ".join(parts))
                    row_count += 1
            except Exception:
                error_count += 1
                continue

        if error_count > 0:
            logger.warning(
                "CSV parsing had errors",
                filename=filename,
                rows_parsed=row_count,
                rows_errored=error_count,
            )

    except csv.Error as e:
        # Fall back to line-by-line parsing for badly malformed CSVs
        logger.warning("CSV parsing failed, falling back to line-by-line", filename=filename, error=str(e))
        lines = [line.strip() for line in content.split("\n") if line.strip()]

    return "\n".join(lines)


def _parse_json(content: str, filename: str) -> str:
    """Parse JSON files into readable text.

    Recursively extracts all string values from the JSON structure,
    preserving key names for context.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid JSON in {filename}: {e}") from e

    text_parts = []
    _extract_json_text(data, text_parts, prefix="")
    return "\n".join(text_parts)


def _extract_json_text(data: object, parts: list[str], prefix: str) -> None:
    """Recursively extract text from JSON structures."""
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            _extract_json_text(value, parts, new_prefix)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_prefix = f"{prefix}[{i}]"
            _extract_json_text(item, parts, new_prefix)
    elif isinstance(data, str) and data.strip() or isinstance(data, (int, float, bool)):
        parts.append(f"{prefix}: {data}")
