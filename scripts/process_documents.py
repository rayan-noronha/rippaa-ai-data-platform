"""Process documents from the raw-documents Kafka topic.

Consumes ingested document events and runs them through:
parse → chunk → PII detect → mask → embed → store in pgvector

Usage:
    python -m scripts.process_documents [--max-messages 53]
"""

import argparse
import time


def main() -> None:
    """Run document processing consumer."""
    parser = argparse.ArgumentParser(description="Process documents from Kafka")
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        help="Maximum number of documents to process (default: all available)",
    )
    args = parser.parse_args()

    from src.processing.consumer import consume_and_process

    print("🔄 RIPPAA AI Data Platform — Document Processing")
    print(f"   Max messages: {args.max_messages or 'all available'}")
    print()

    start_time = time.time()
    results = consume_and_process(max_messages=args.max_messages)
    elapsed = time.time() - start_time

    # Summary
    succeeded = [r for r in results if r.get("status") == "processed"]
    failed = [r for r in results if r.get("status") == "failed"]
    total_chunks = sum(r.get("chunks_created", 0) for r in succeeded)
    total_pii = sum(r.get("pii_detections", 0) for r in succeeded)

    print()
    print(f"✅ Processed:      {len(succeeded)} documents")
    if failed:
        print(f"❌ Failed:         {len(failed)} documents")
        for f in failed:
            print(f"   • {f.get('filename', 'unknown')}: {f.get('error', 'unknown')}")
    print(f"📄 Chunks created: {total_chunks}")
    print(f"🔒 PII detections: {total_pii}")
    print(f"⏱️  Time:           {elapsed:.1f}s")
    print()
    print("📊 Verify results:")
    print('   • Chunks: docker exec rippaa-postgres psql -U rippaa -d rippaa_platform -c "SELECT count(*) FROM chunks"')
    print('   • PII:    docker exec rippaa-postgres psql -U rippaa -d rippaa_platform -c "SELECT entity_type, count(*) FROM pii_detections GROUP BY entity_type"')
    print('   • Status: docker exec rippaa-postgres psql -U rippaa -d rippaa_platform -c "SELECT status, count(*) FROM documents GROUP BY status"')


if __name__ == "__main__":
    main()
