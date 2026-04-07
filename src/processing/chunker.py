"""Text chunker — splits documents into manageable chunks for embedding.

Supports multiple chunking strategies:
- fixed_size: Split by character count with overlap
- sliding_window: Overlapping windows of fixed size

Each chunk targets ~500 tokens (roughly 2000 characters) to balance:
- Embedding quality (too large = diluted meaning)
- Retrieval precision (too small = lost context)
- Cost (fewer chunks = fewer embedding API calls)
"""

import structlog

logger = structlog.get_logger(__name__)

# Rough approximation: 1 token ≈ 4 characters for English text
CHARS_PER_TOKEN = 4
DEFAULT_CHUNK_SIZE_TOKENS = 500
DEFAULT_OVERLAP_TOKENS = 50


def chunk_text(
    text: str,
    strategy: str = "fixed_size",
    chunk_size_tokens: int = DEFAULT_CHUNK_SIZE_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[dict]:
    """Split text into chunks using the specified strategy.

    Args:
        text: The full document text to chunk.
        strategy: Chunking strategy ('fixed_size' or 'sliding_window').
        chunk_size_tokens: Target size per chunk in tokens.
        overlap_tokens: Number of overlapping tokens between consecutive chunks.

    Returns:
        List of chunk dictionaries with keys:
        - chunk_index: Position in the document (0-based)
        - chunk_text: The text content of this chunk
        - token_count: Estimated token count
        - char_start: Character offset where this chunk starts
        - char_end: Character offset where this chunk ends
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    strategy_map = {
        "fixed_size": _chunk_fixed_size,
        "sliding_window": _chunk_sliding_window,
    }

    chunker = strategy_map.get(strategy)
    if chunker is None:
        logger.warning(f"Unknown strategy '{strategy}', falling back to fixed_size")
        chunker = _chunk_fixed_size

    chunks = chunker(text, chunk_size_tokens, overlap_tokens)

    logger.info(
        "Text chunked",
        strategy=strategy,
        total_chars=len(text),
        num_chunks=len(chunks),
        avg_tokens=sum(c["token_count"] for c in chunks) // max(len(chunks), 1),
    )

    return chunks


def _chunk_fixed_size(
    text: str,
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> list[dict]:
    """Split text into fixed-size chunks with overlap.

    Tries to split at sentence boundaries when possible,
    falling back to word boundaries, then character boundaries.
    """
    chunk_size_chars = chunk_size_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN

    if len(text) <= chunk_size_chars:
        # Document fits in a single chunk
        return [
            {
                "chunk_index": 0,
                "chunk_text": text,
                "token_count": _estimate_tokens(text),
                "char_start": 0,
                "char_end": len(text),
            }
        ]

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        # Calculate end position
        end = start + chunk_size_chars

        end = len(text) if end >= len(text) else _find_break_point(text, start, end)

        chunk_text = text[start:end].strip()

        if chunk_text:
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "token_count": _estimate_tokens(chunk_text),
                    "char_start": start,
                    "char_end": end,
                }
            )
            chunk_index += 1

        # Move start forward, accounting for overlap
        start = end - overlap_chars
        if start <= chunks[-1]["char_start"] if chunks else 0:
            # Prevent infinite loop if overlap is too large
            start = end

    return chunks


def _chunk_sliding_window(
    text: str,
    chunk_size_tokens: int,
    overlap_tokens: int,
) -> list[dict]:
    """Split text using a sliding window approach.

    Similar to fixed_size but ensures consistent overlap.
    Better for documents where context spans chunk boundaries.
    """
    chunk_size_chars = chunk_size_tokens * CHARS_PER_TOKEN
    step_chars = (chunk_size_tokens - overlap_tokens) * CHARS_PER_TOKEN

    if step_chars <= 0:
        step_chars = chunk_size_chars // 2

    if len(text) <= chunk_size_chars:
        return [
            {
                "chunk_index": 0,
                "chunk_text": text,
                "token_count": _estimate_tokens(text),
                "char_start": 0,
                "char_end": len(text),
            }
        ]

    chunks = []
    chunk_index = 0
    start = 0

    while start < len(text):
        end = min(start + chunk_size_chars, len(text))

        # Try to find a clean break if not at the end
        if end < len(text):
            end = _find_break_point(text, start, end)

        chunk_text = text[start:end].strip()

        if chunk_text:
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "token_count": _estimate_tokens(chunk_text),
                    "char_start": start,
                    "char_end": end,
                }
            )
            chunk_index += 1

        start += step_chars

        # Don't create a tiny final chunk
        if start < len(text) and (len(text) - start) < (chunk_size_chars // 4):
            # Extend previous chunk to include the remainder
            chunk_text = text[start:].strip()
            if chunk_text and chunks:
                last = chunks[-1]
                last["chunk_text"] = text[last["char_start"] :].strip()
                last["char_end"] = len(text)
                last["token_count"] = _estimate_tokens(last["chunk_text"])
            break

    return chunks


def _find_break_point(text: str, start: int, end: int) -> int:
    """Find the best break point near the target end position.

    Priority: sentence boundary > paragraph boundary > word boundary > exact position.
    Searches backwards from end position within a reasonable window.
    """
    search_window = min(200, (end - start) // 4)
    search_start = max(start, end - search_window)
    window = text[search_start:end]

    # Try sentence boundaries (. ! ? followed by space or newline)
    for sep in [". ", ".\n", "! ", "!\n", "? ", "?\n"]:
        last_pos = window.rfind(sep)
        if last_pos != -1:
            return search_start + last_pos + len(sep)

    # Try paragraph boundaries
    last_newline = window.rfind("\n\n")
    if last_newline != -1:
        return search_start + last_newline + 2

    # Try single newline
    last_newline = window.rfind("\n")
    if last_newline != -1:
        return search_start + last_newline + 1

    # Try word boundary (space)
    last_space = window.rfind(" ")
    if last_space != -1:
        return search_start + last_space + 1

    # No good break point found — split at exact position
    return end


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text length.

    Uses the rough approximation of 4 characters per token.
    For exact counts, use tiktoken — but this is sufficient
    for chunking decisions.
    """
    return max(1, len(text) // CHARS_PER_TOKEN)
