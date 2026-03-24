"""Tests for shared domain models."""

from uuid import uuid4

from src.shared.models import (
    ChunkStrategy,
    DocumentChunk,
    DocumentMetadata,
    DocumentStatus,
    FileType,
    HealthResponse,
    IngestRequest,
    PIIDetection,
    PIIEntityType,
    QueryRequest,
    SourceDomain,
)


class TestDocumentMetadata:
    """Test document metadata model."""

    def test_create_with_defaults(self) -> None:
        """Should create document with default status and auto-generated ID."""
        doc = DocumentMetadata(
            filename="test-policy.pdf",
            source_domain=SourceDomain.INSURANCE,
            file_type=FileType.PDF,
            file_size_bytes=1024,
            s3_raw_key="landing/test-policy.pdf",
        )
        assert doc.id is not None
        assert doc.status == DocumentStatus.INGESTED
        assert doc.error_message is None
        assert doc.processed_at is None

    def test_all_source_domains(self) -> None:
        """All four source domains should be valid."""
        for domain in SourceDomain:
            doc = DocumentMetadata(
                filename="test.pdf",
                source_domain=domain,
                file_type=FileType.PDF,
                file_size_bytes=100,
                s3_raw_key="landing/test.pdf",
            )
            assert doc.source_domain == domain

    def test_all_file_types(self) -> None:
        """All supported file types should be valid."""
        for ft in FileType:
            doc = DocumentMetadata(
                filename=f"test.{ft.value}",
                source_domain=SourceDomain.ENTERPRISE,
                file_type=ft,
                file_size_bytes=100,
                s3_raw_key=f"landing/test.{ft.value}",
            )
            assert doc.file_type == ft


class TestDocumentChunk:
    """Test document chunk model."""

    def test_create_chunk(self) -> None:
        """Should create a chunk with all required fields."""
        chunk = DocumentChunk(
            document_id=uuid4(),
            chunk_index=0,
            chunk_text="This is a test chunk of text.",
            chunk_strategy=ChunkStrategy.FIXED_SIZE,
            token_count=8,
        )
        assert chunk.embedding is None
        assert chunk.pii_detected is False
        assert chunk.pii_masked is False
        assert chunk.metadata == {}

    def test_chunk_with_embedding(self) -> None:
        """Should accept an embedding vector."""
        embedding = [0.1] * 1024
        chunk = DocumentChunk(
            document_id=uuid4(),
            chunk_index=0,
            chunk_text="Test chunk.",
            chunk_strategy=ChunkStrategy.SEMANTIC,
            token_count=3,
            embedding=embedding,
        )
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 1024


class TestPIIDetection:
    """Test PII detection model."""

    def test_create_pii_detection(self) -> None:
        """Should record a PII detection with masking."""
        pii = PIIDetection(
            document_id=uuid4(),
            chunk_id=uuid4(),
            entity_type=PIIEntityType.EMAIL,
            confidence=0.95,
            original_text="john@example.com",
            masked_text="[EMAIL_REDACTED]",
        )
        assert pii.entity_type == PIIEntityType.EMAIL
        assert pii.confidence == 0.95

    def test_all_pii_entity_types(self) -> None:
        """All PII entity types should be valid."""
        for entity_type in PIIEntityType:
            pii = PIIDetection(
                document_id=uuid4(),
                entity_type=entity_type,
                confidence=0.8,
                original_text="test",
                masked_text="[REDACTED]",
            )
            assert pii.entity_type == entity_type


class TestAPIModels:
    """Test API request/response models."""

    def test_ingest_request(self) -> None:
        """Should create a valid ingest request."""
        req = IngestRequest(
            filename="claims-report-q3.pdf",
            source_domain=SourceDomain.INSURANCE,
            file_type=FileType.PDF,
        )
        assert req.filename == "claims-report-q3.pdf"

    def test_query_request_defaults(self) -> None:
        """Query request should have sensible defaults."""
        req = QueryRequest(query="What is the claims process?")
        assert req.max_results == 5
        assert req.source_domains is None

    def test_query_request_with_filters(self) -> None:
        """Query request should accept domain filters."""
        req = QueryRequest(
            query="What are the compliance requirements?",
            max_results=10,
            source_domains=[SourceDomain.INSURANCE, SourceDomain.FINANCIAL],
        )
        assert len(req.source_domains) == 2

    def test_health_response(self) -> None:
        """Health response should report dependency status."""
        health = HealthResponse(
            status="healthy",
            version="0.1.0",
            dependencies={"postgres": "healthy", "kafka": "healthy", "s3": "healthy"},
        )
        assert health.status == "healthy"
        assert len(health.dependencies) == 3
