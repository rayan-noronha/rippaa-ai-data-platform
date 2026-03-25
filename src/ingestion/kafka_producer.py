"""Kafka producer for publishing document ingestion events."""

import json
from uuid import UUID

import structlog
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

from src.shared.config import get_settings

logger = structlog.get_logger(__name__)

# Module-level producer instance (reused across calls)
_producer: Producer | None = None


def _json_serializer(obj: object) -> str:
    """Handle UUID and other non-serializable types."""
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def get_producer() -> Producer:
    """Get or create a Kafka producer instance."""
    global _producer
    if _producer is None:
        settings = get_settings()
        _producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "client.id": "rippaa-ingestion",
            "acks": "all",  # Wait for all replicas to acknowledge
            "retries": 3,
            "retry.backoff.ms": 1000,
        })
        logger.info("Kafka producer created", servers=settings.kafka_bootstrap_servers)
    return _producer


def ensure_topics_exist() -> None:
    """Create Kafka topics if they don't exist."""
    settings = get_settings()
    admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})

    topics = [
        NewTopic(
            topic=settings.kafka_raw_documents_topic,
            num_partitions=3,
            replication_factor=1,
        ),
        NewTopic(
            topic=settings.kafka_processed_chunks_topic,
            num_partitions=3,
            replication_factor=1,
        ),
    ]

    # Check which topics already exist
    existing = admin.list_topics(timeout=10).topics
    new_topics = [t for t in topics if t.topic not in existing]

    if new_topics:
        futures = admin.create_topics(new_topics)
        for topic_name, future in futures.items():
            try:
                future.result()
                logger.info("Created Kafka topic", topic=topic_name)
            except Exception as e:
                if "already exists" not in str(e):
                    logger.error("Failed to create topic", topic=topic_name, error=str(e))
    else:
        logger.debug("All Kafka topics already exist")


def publish_document_event(
    document_id: str,
    filename: str,
    source_domain: str,
    file_type: str,
    s3_key: str,
    file_size_bytes: int,
) -> None:
    """Publish a document ingestion event to Kafka.

    The message is keyed by document_id to ensure all events
    for the same document go to the same partition (ordering guarantee).
    """
    settings = get_settings()
    producer = get_producer()

    event = {
        "document_id": document_id,
        "filename": filename,
        "source_domain": source_domain,
        "file_type": file_type,
        "s3_key": s3_key,
        "file_size_bytes": file_size_bytes,
    }

    producer.produce(
        topic=settings.kafka_raw_documents_topic,
        key=document_id,
        value=json.dumps(event, default=_json_serializer),
        callback=_delivery_callback,
    )

    # Flush to ensure the message is sent (in production, you'd batch these)
    producer.flush(timeout=10)


def _delivery_callback(err: object, msg: object) -> None:
    """Callback for Kafka message delivery confirmation."""
    if err is not None:
        logger.error("Kafka delivery failed", error=str(err))
    else:
        logger.debug(
            "Kafka message delivered",
            topic=msg.topic(),
            partition=msg.partition(),
            offset=msg.offset(),
        )


def check_kafka_health() -> bool:
    """Verify Kafka connectivity."""
    try:
        settings = get_settings()
        admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
        cluster_metadata = admin.list_topics(timeout=5)
        return cluster_metadata is not None
    except Exception:
        logger.exception("Kafka health check failed")
        return False
