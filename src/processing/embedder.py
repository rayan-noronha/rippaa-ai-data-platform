"""Embedding generator — converts text chunks into vector embeddings.

Two modes:
- 'local': Generates deterministic embeddings using text hashing (free, fast, for development)
- 'bedrock': Uses Amazon Titan Embed via Bedrock (production quality, costs money)

The local mode produces consistent embeddings — same text always gets the same vector.
This is sufficient for testing the full pipeline. Production uses real embeddings.
"""

import hashlib
import math
from typing import Literal

import structlog

from src.shared.config import get_settings

logger = structlog.get_logger(__name__)

EMBEDDING_DIMENSION = 1024


def generate_embedding(
    text: str,
    mode: Literal["local", "bedrock"] | None = None,
) -> list[float]:
    """Generate a vector embedding for a text chunk.

    Args:
        text: The text to embed.
        mode: Override the embedding mode. If None, reads from config.

    Returns:
        List of floats representing the embedding vector (1024 dimensions).
    """
    if mode is None:
        settings = get_settings()
        mode = "bedrock" if settings.llm_provider == "bedrock" and settings.environment == "production" else "local"

    if mode == "bedrock":
        return _generate_bedrock_embedding(text)
    else:
        return _generate_local_embedding(text)


def generate_embeddings_batch(
    texts: list[str],
    mode: Literal["local", "bedrock"] | None = None,
) -> list[list[float]]:
    """Generate embeddings for a batch of text chunks.

    Args:
        texts: List of texts to embed.
        mode: Override the embedding mode.

    Returns:
        List of embedding vectors.
    """
    # For local mode, process individually (it's fast)
    # For Bedrock, we'd want to batch — but Titan doesn't support batch embedding
    return [generate_embedding(text, mode=mode) for text in texts]


def _generate_local_embedding(text: str) -> list[float]:
    """Generate a deterministic embedding from text using hashing.

    This is NOT a real semantic embedding — similar texts won't have
    similar vectors. But it produces consistent, valid vectors for
    testing the full pipeline (storage, retrieval, pgvector indexing).

    How it works:
    1. Hash the text with SHA-512 (64 bytes)
    2. Repeat the hash to fill 1024 dimensions
    3. Convert each byte to a float in [-1, 1]
    4. Normalize to unit length (cosine similarity requirement)
    """
    # Create hash of the text
    text_hash = hashlib.sha512(text.encode("utf-8")).digest()

    # Repeat hash bytes to fill the embedding dimension
    repeated = (text_hash * ((EMBEDDING_DIMENSION // len(text_hash)) + 1))[:EMBEDDING_DIMENSION]

    # Convert bytes to floats in [-1, 1]
    raw = [(b / 127.5) - 1.0 for b in repeated]

    # Add variation based on text length and first few characters
    # This gives slightly different embeddings for different texts
    length_factor = (len(text) % 100) / 100.0
    for i in range(min(len(text), EMBEDDING_DIMENSION)):
        raw[i] += (ord(text[i]) / 255.0 - 0.5) * 0.1
        raw[i] += length_factor * 0.05

    # L2 normalize to unit length
    magnitude = math.sqrt(sum(x * x for x in raw))
    embedding = [x / magnitude for x in raw] if magnitude > 0 else raw

    logger.debug("Generated local embedding", text_length=len(text), dimensions=len(embedding))
    return embedding


def _generate_bedrock_embedding(text: str) -> list[float]:
    """Generate embedding using Amazon Titan via Bedrock.

    Requires AWS credentials and Bedrock access.
    Used in production; local dev should use 'local' mode.
    """
    import json

    import boto3

    settings = get_settings()

    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
    )

    body = json.dumps(
        {
            "inputText": text[:8192],  # Titan has a max input length
        }
    )

    response = client.invoke_model(
        modelId=settings.embedding_model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    embedding = result["embedding"]

    logger.debug("Generated Bedrock embedding", text_length=len(text), dimensions=len(embedding))
    return embedding
