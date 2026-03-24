"""Application configuration — loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the RIPPAA AI Data Platform.

    All values can be overridden via environment variables.
    For local development, defaults point to Docker Compose services.
    """

    # ── Application ──────────────────────────────
    app_name: str = "rippaa-ai-data-platform"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production
    debug: bool = True
    log_level: str = "INFO"

    # ── Database (PostgreSQL + pgvector) ─────────
    database_url: str = "postgresql://rippaa:rippaa_dev@localhost:5432/rippaa_platform"

    # ── Kafka ────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_raw_documents_topic: str = "raw-documents"
    kafka_processed_chunks_topic: str = "processed-chunks"
    kafka_consumer_group: str = "rippaa-processors"

    # ── AWS / LocalStack ─────────────────────────
    aws_region: str = "ap-southeast-2"
    aws_endpoint_url: str | None = "http://localhost:4566"  # None in production
    s3_landing_bucket: str = "rippaa-landing"
    s3_processed_bucket: str = "rippaa-processed"

    # ── LLM (Claude via Bedrock) ─────────────────
    llm_provider: str = "bedrock"  # bedrock | anthropic
    llm_model_id: str = "anthropic.claude-sonnet-4-20250514"
    anthropic_api_key: str | None = None  # Only needed if llm_provider = anthropic

    # ── Embedding ────────────────────────────────
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    embedding_dimension: int = 1024

    # ── PII Detection ────────────────────────────
    pii_detection_enabled: bool = True
    pii_confidence_threshold: float = 0.7

    # ── API ──────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_rate_limit: int = 100  # requests per minute

    model_config = {"env_prefix": "RIPPAA_", "env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
