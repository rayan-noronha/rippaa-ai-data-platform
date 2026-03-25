"""Document ingestion service.

Orchestrates the full ingestion flow:
1. Upload document to S3 landing bucket
2. Register document in PostgreSQL
3. Publish event to Kafka for downstream processing
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import structlog
from sqlalchemy import text

from src.shared.config import get_settings
from src.shared.database import get_engine
from src.ingestion.s3_client import ensure_bucket_exists, upload_file_to_s3
from src.ingestion.kafka_producer import ensure_topics_exist, publish_document_event

logger = structlog.get_logger(__name__)


def ingest_document(
    file_path: str,
    source_domain: str,
    file_type: str,
) -> dict:
    """Ingest a single document into the platform.

    Args:
        file_path: Local path to the document file.
        source_domain: Industry domain (insurance, financial, government, enterprise).
        file_type: File format (txt, csv, json, pdf, docx).

    Returns:
        Dictionary with document_id, s3_key, and status.
    """
    settings = get_settings()
    filename = os.path.basename(file_path)
    document_id = str(uuid4())
    file_size = os.path.getsize(file_path)

    # Build S3 key: {domain}/{YYYY}/{MM}/{document_id}/{filename}
    now = datetime.now(timezone.utc)
    s3_key = f"{source_domain}/{now.year}/{now.month:02d}/{document_id}/{filename}"

    logger.info(
        "Ingesting document",
        document_id=document_id,
        filename=filename,
        domain=source_domain,
        file_type=file_type,
        size_bytes=file_size,
    )

    # Step 1: Upload to S3
    upload_file_to_s3(
        file_path=file_path,
        bucket=settings.s3_landing_bucket,
        s3_key=s3_key,
    )

    # Step 2: Register in PostgreSQL
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO documents (id, filename, source_domain, file_type, file_size_bytes, s3_raw_key, status)
                VALUES (:id, :filename, :source_domain, :file_type, :file_size_bytes, :s3_raw_key, 'ingested')
            """),
            {
                "id": document_id,
                "filename": filename,
                "source_domain": source_domain,
                "file_type": file_type,
                "file_size_bytes": file_size,
                "s3_raw_key": s3_key,
            },
        )
        conn.commit()

    logger.info("Document registered in database", document_id=document_id)

    # Step 3: Publish to Kafka
    publish_document_event(
        document_id=document_id,
        filename=filename,
        source_domain=source_domain,
        file_type=file_type,
        s3_key=s3_key,
        file_size_bytes=file_size,
    )

    logger.info("Document ingestion complete", document_id=document_id, s3_key=s3_key)

    return {
        "document_id": document_id,
        "filename": filename,
        "s3_key": s3_key,
        "status": "ingested",
    }


def ingest_directory(directory: str) -> list[dict]:
    """Ingest all documents from a directory (and subdirectories).

    Reads metadata sidecar files (.meta.json) to determine
    source_domain and file_type for each document.

    Args:
        directory: Path to directory containing documents.

    Returns:
        List of ingestion results.
    """
    import json

    settings = get_settings()
    directory_path = Path(directory)

    if not directory_path.exists():
        logger.error("Directory not found", directory=directory)
        return []

    # Ensure infrastructure is ready
    ensure_bucket_exists(settings.s3_landing_bucket)
    ensure_topics_exist()

    results = []
    # Find all non-meta files
    all_files = sorted(directory_path.rglob("*"))
    document_files = [f for f in all_files if f.is_file() and ".meta.json" not in f.name and f.name != "manifest.json"]

    logger.info("Starting batch ingestion", directory=directory, total_files=len(document_files))

    for file_path in document_files:
        # Look for metadata sidecar
        meta_path = Path(str(file_path) + ".meta.json")
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            source_domain = meta.get("source_domain", "enterprise")
            file_type = meta.get("file_type", "txt")
        else:
            # Infer from directory structure and extension
            source_domain = file_path.parent.name
            file_type = file_path.suffix.lstrip(".")

        try:
            result = ingest_document(
                file_path=str(file_path),
                source_domain=source_domain,
                file_type=file_type if file_type != "csv_raw" else "csv",
            )
            results.append(result)
        except Exception:
            logger.exception("Failed to ingest document", file=str(file_path))
            results.append({
                "filename": file_path.name,
                "status": "failed",
                "error": "See logs for details",
            })

    # Summary
    succeeded = sum(1 for r in results if r.get("status") == "ingested")
    failed = sum(1 for r in results if r.get("status") == "failed")
    logger.info(
        "Batch ingestion complete",
        total=len(results),
        succeeded=succeeded,
        failed=failed,
    )

    return results
