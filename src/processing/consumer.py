"""Kafka consumer for document processing.

Consumes events from the 'raw-documents' topic and runs each
document through the processing pipeline (parse → chunk → PII → embed → store).

Can be run as a standalone worker or called from a script.
"""

import json
import signal

import structlog
from confluent_kafka import Consumer, KafkaError

from src.processing.pipeline import process_document
from src.shared.config import get_settings

logger = structlog.get_logger(__name__)

# Graceful shutdown flag
_running = True


def _signal_handler(signum: int, frame: object) -> None:
    """Handle shutdown signals gracefully."""
    global _running
    logger.info("Shutdown signal received, finishing current document...")
    _running = False


def create_consumer() -> Consumer:
    """Create a Kafka consumer for the raw-documents topic."""
    settings = get_settings()
    return Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
            "auto.commit.interval.ms": 5000,
        }
    )


def consume_and_process(max_messages: int | None = None) -> list[dict]:
    """Consume documents from Kafka and process them.

    Args:
        max_messages: Maximum number of messages to process.
                     None = run indefinitely until shutdown signal.

    Returns:
        List of processing results.
    """
    global _running
    _running = True

    settings = get_settings()
    consumer = create_consumer()
    consumer.subscribe([settings.kafka_raw_documents_topic])

    results = []
    processed_count = 0

    logger.info(
        "Kafka consumer started",
        topic=settings.kafka_raw_documents_topic,
        group=settings.kafka_consumer_group,
        max_messages=max_messages or "unlimited",
    )

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        while _running:
            if max_messages and processed_count >= max_messages:
                logger.info("Reached max messages limit", count=processed_count)
                break

            msg = consumer.poll(timeout=5.0)

            if msg is None:
                if max_messages:
                    # In bounded mode, no more messages = we're done
                    logger.info("No more messages in topic")
                    break
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    if max_messages:
                        break
                    continue
                logger.error("Kafka consumer error", error=msg.error())
                continue

            # Parse the message
            try:
                event = json.loads(msg.value().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error("Failed to parse Kafka message", error=str(e))
                continue

            # Process the document
            result = process_document(
                document_id=event["document_id"],
                filename=event["filename"],
                source_domain=event["source_domain"],
                file_type=event["file_type"],
                s3_key=event["s3_key"],
            )

            results.append(result)
            processed_count += 1

            logger.info(
                "Progress",
                processed=processed_count,
                max=max_messages or "unlimited",
                last_status=result["status"],
            )

    except Exception:
        logger.exception("Unexpected error in consumer loop")
    finally:
        consumer.close()
        logger.info("Kafka consumer stopped", total_processed=processed_count)

    return results
