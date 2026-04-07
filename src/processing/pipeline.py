"""Document processing pipeline.

Orchestrates the full processing flow for a single document:
1. Download from S3
2. Parse document text
3. Chunk text into segments
4. Detect and mask PII
5. Generate embeddings
6. Store chunks + embeddings in pgvector
7. Log quality metrics
"""

import json
import time
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.ingestion.s3_client import get_s3_client
from src.processing.chunker import chunk_text
from src.processing.embedder import generate_embedding
from src.processing.parser import ParseError, parse_document
from src.processing.pii_detector import detect_pii, mask_text
from src.shared.config import get_settings
from src.shared.database import get_engine

logger = structlog.get_logger(__name__)


def process_document(
    document_id: str,
    filename: str,
    source_domain: str,
    file_type: str,
    s3_key: str,
) -> dict[str, Any]:
    """Process a single document through the full pipeline."""
    settings = get_settings()
    engine = get_engine()
    start_time = time.time()

    logger.info(
        "Processing document",
        document_id=document_id,
        filename=filename,
        domain=source_domain,
    )

    _update_document_status(engine, document_id, "processing")

    try:
        raw_content = _download_from_s3(settings.s3_landing_bucket, s3_key)
        parsed_text = parse_document(raw_content, file_type, filename)

        chunks = chunk_text(
            text=parsed_text,
            strategy="fixed_size",
            chunk_size_tokens=500,
            overlap_tokens=50,
        )

        if not chunks:
            raise ParseError(f"No chunks generated from {filename}")

        total_pii_detections = []
        masked_chunks: list[dict[str, Any]] = []

        for chunk in chunks:
            pii_matches = detect_pii(
                chunk["chunk_text"],
                confidence_threshold=settings.pii_confidence_threshold,
            )

            masked_text = mask_text(chunk["chunk_text"], pii_matches)

            masked_chunks.append(
                {
                    **chunk,
                    "original_text": chunk["chunk_text"],
                    "chunk_text": masked_text,
                    "pii_detected": len(pii_matches) > 0,
                    "pii_matches": pii_matches,
                }
            )

            total_pii_detections.extend(pii_matches)

        for chunk in masked_chunks:
            chunk["embedding"] = generate_embedding(chunk["chunk_text"])

        _store_chunks(engine, document_id, masked_chunks)

        if total_pii_detections:
            _store_pii_detections(engine, document_id, masked_chunks)

        elapsed = time.time() - start_time
        _update_document_status(engine, document_id, "processed")
        _log_quality_metrics(
            engine,
            document_id,
            chunks_count=len(masked_chunks),
            pii_count=len(total_pii_detections),
            elapsed_seconds=elapsed,
        )

        result: dict[str, Any] = {
            "document_id": document_id,
            "filename": filename,
            "status": "processed",
            "chunks_created": len(masked_chunks),
            "pii_detections": len(total_pii_detections),
            "elapsed_seconds": round(elapsed, 2),
        }

        logger.info("Document processed successfully", **result)
        return result

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        _update_document_status(engine, document_id, "failed", error_msg)
        _log_quality_metrics(
            engine,
            document_id,
            chunks_count=0,
            pii_count=0,
            elapsed_seconds=elapsed,
            error=error_msg,
        )

        logger.error(
            "Document processing failed",
            document_id=document_id,
            filename=filename,
            error=error_msg,
        )

        return {
            "document_id": document_id,
            "filename": filename,
            "status": "failed",
            "error": error_msg,
            "elapsed_seconds": round(elapsed, 2),
        }


def _download_from_s3(bucket: str, s3_key: str) -> bytes:
    """Download a file from S3 and return its content."""
    s3 = get_s3_client()
    response = s3.get_object(Bucket=bucket, Key=s3_key)
    content: bytes = response["Body"].read()
    logger.debug("Downloaded from S3", bucket=bucket, key=s3_key, size=len(content))
    return content


def _update_document_status(
    engine: Engine,
    document_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update document status in the registry."""
    with engine.connect() as conn:
        if status == "processed":
            conn.execute(
                text("""
                    UPDATE documents
                    SET status = :status, processed_at = NOW(), updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": document_id, "status": status},
            )
        elif status == "failed":
            conn.execute(
                text("""
                    UPDATE documents
                    SET status = :status, error_message = :error, updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": document_id, "status": status, "error": error_message},
            )
        else:
            conn.execute(
                text("""
                    UPDATE documents
                    SET status = :status, updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": document_id, "status": status},
            )
        conn.commit()


def _store_chunks(engine: Engine, document_id: str, chunks: list[dict[str, Any]]) -> None:
    """Store processed chunks with embeddings in pgvector."""
    with engine.connect() as conn:
        for chunk in chunks:
            chunk_id = str(uuid4())
            embedding_str = "[" + ",".join(str(x) for x in chunk["embedding"]) + "]"

            conn.execute(
                text("""
                    INSERT INTO chunks (id, document_id, chunk_index, chunk_text, chunk_strategy,
                                       token_count, embedding, pii_detected, pii_masked, metadata)
                    VALUES (:id, :document_id, :chunk_index, :chunk_text, :chunk_strategy,
                            :token_count, :embedding, :pii_detected, :pii_masked, :metadata)
                """),
                {
                    "id": chunk_id,
                    "document_id": document_id,
                    "chunk_index": chunk["chunk_index"],
                    "chunk_text": chunk["chunk_text"],
                    "chunk_strategy": "fixed_size",
                    "token_count": chunk["token_count"],
                    "embedding": embedding_str,
                    "pii_detected": chunk["pii_detected"],
                    "pii_masked": chunk["pii_detected"],
                    "metadata": json.dumps(
                        {
                            "char_start": chunk["char_start"],
                            "char_end": chunk["char_end"],
                        }
                    ),
                },
            )

            for match in chunk.get("pii_matches", []):
                conn.execute(
                    text("""
                        INSERT INTO pii_detections (id, document_id, chunk_id, entity_type,
                                                    confidence, original_text, masked_text)
                        VALUES (:id, :document_id, :chunk_id, :entity_type,
                                :confidence, :original_text, :masked_text)
                    """),
                    {
                        "id": str(uuid4()),
                        "document_id": document_id,
                        "chunk_id": chunk_id,
                        "entity_type": match.entity_type,
                        "confidence": match.confidence,
                        "original_text": match.text,
                        "masked_text": match.masked_text,
                    },
                )

        conn.commit()

    logger.info("Stored chunks in pgvector", document_id=document_id, chunk_count=len(chunks))


def _store_pii_detections(engine: Engine, document_id: str, chunks: list[dict[str, Any]]) -> None:
    """PII detections are stored inline with chunks in _store_chunks."""
    pass


def _log_quality_metrics(
    engine: Engine,
    document_id: str,
    chunks_count: int,
    pii_count: int,
    elapsed_seconds: float,
    error: str | None = None,
) -> None:
    """Log processing quality metrics."""
    status = "pass" if error is None else "fail"
    details: dict[str, Any] = {
        "chunks_created": chunks_count,
        "pii_detections": pii_count,
        "elapsed_seconds": round(elapsed_seconds, 2),
    }
    if error:
        details["error"] = error

    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO quality_metrics (id, document_id, metric_type, status, details)
                VALUES (:id, :document_id, 'processing', :status, :details)
            """),
            {
                "id": str(uuid4()),
                "document_id": document_id,
                "status": status,
                "details": json.dumps(details),
            },
        )
        conn.commit()
