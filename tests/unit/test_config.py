"""Tests for shared configuration module."""

import os
from unittest.mock import patch

from src.shared.config import Settings, get_settings


class TestSettings:
    """Test application settings loading."""

    def test_default_settings(self) -> None:
        """Settings should load with sensible defaults."""
        settings = Settings()
        assert settings.app_name == "rippaa-ai-data-platform"
        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.api_port == 8000

    def test_database_url_default(self) -> None:
        """Default database URL should point to local Docker Compose PostgreSQL."""
        settings = Settings()
        assert "localhost:5432" in settings.database_url
        assert "rippaa_platform" in settings.database_url

    def test_kafka_defaults(self) -> None:
        """Kafka settings should default to local Docker Compose."""
        settings = Settings()
        assert settings.kafka_bootstrap_servers == "localhost:9092"
        assert settings.kafka_raw_documents_topic == "raw-documents"
        assert settings.kafka_processed_chunks_topic == "processed-chunks"

    def test_pii_detection_enabled_by_default(self) -> None:
        """PII detection should be enabled by default."""
        settings = Settings()
        assert settings.pii_detection_enabled is True
        assert settings.pii_confidence_threshold == 0.7

    @patch.dict(os.environ, {"RIPPAA_ENVIRONMENT": "production", "RIPPAA_DEBUG": "false"})
    def test_environment_override(self) -> None:
        """Settings should be overridable via environment variables."""
        settings = Settings()
        assert settings.environment == "production"
        assert settings.debug is False

    @patch.dict(os.environ, {"RIPPAA_API_PORT": "9000"})
    def test_port_override(self) -> None:
        """API port should be overridable."""
        settings = Settings()
        assert settings.api_port == 9000
