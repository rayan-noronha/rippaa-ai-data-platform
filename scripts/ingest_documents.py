"""Ingest synthetic documents into the RIPPAA AI Data Platform.

Uploads documents to S3, registers them in PostgreSQL,
and publishes events to Kafka for downstream processing.

Usage:
    python scripts/ingest_documents.py [--data-dir data/synthetic]
"""

import argparse
import sys
import time

from src.ingestion.service import ingest_directory


def main() -> None:
    """Run document ingestion."""
    parser = argparse.ArgumentParser(description="Ingest documents into RIPPAA AI Data Platform")
    parser.add_argument("--data-dir", type=str, default="data/synthetic", help="Directory containing documents to ingest")
    args = parser.parse_args()

    print("🚀 RIPPAA AI Data Platform — Document Ingestion")
    print(f"   Source: {args.data_dir}")
    print()

    start_time = time.time()
    results = ingest_directory(args.data_dir)
    elapsed = time.time() - start_time

    # Print summary
    succeeded = [r for r in results if r.get("status") == "ingested"]
    failed = [r for r in results if r.get("status") == "failed"]

    print()
    print(f"✅ Ingested: {len(succeeded)} documents")
    if failed:
        print(f"❌ Failed:   {len(failed)} documents")
        for f in failed:
            print(f"   • {f.get('filename', 'unknown')}: {f.get('error', 'unknown error')}")
    print(f"⏱️  Time:     {elapsed:.1f}s")
    print()
    print("📊 Next steps:")
    print("   • Check Kafka UI at http://localhost:8080 — look for messages in 'raw-documents' topic")
    print("   • Query PostgreSQL: docker exec rippaa-postgres psql -U rippaa -d rippaa_platform -c \"SELECT count(*) FROM documents\"")


if __name__ == "__main__":
    main()
