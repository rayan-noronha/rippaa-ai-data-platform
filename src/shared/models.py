"""Domain models for the RIPPAA AI Data Platform."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────


class DocumentStatus(str, Enum):
    """Lifecycle status of an ingested document."""

    INGESTED = "ingested"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class SourceDomain(str, Enum):
    """Industry domain of the source document."""

    INSURANCE = "insurance"
    FINANCIAL = "financial"
    GOVERNMENT = "government"
    ENTERPRISE = "enterprise"


class FileType(str, Enum):
    """Supported file types for ingestion."""

    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    TXT = "txt"
    DOCX = "docx"


class ChunkStrategy(str, Enum):
    """Strategy used to split documents into chunks."""

    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"


class PIIEntityType(str, Enum):
    """Types of PII entities detected."""

    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ABN = "ABN"
    MEDICARE = "MEDICARE"
    ADDRESS = "ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    CREDIT_CARD = "CREDIT_CARD"


# ── Document Models ──────────────────────────────


class DocumentMetadata(BaseModel):
    """Metadata extracted from or assigned to a document."""

    id: UUID = Field(default_factory=uuid4)
    filename: str
    source_domain: SourceDomain
    file_type: FileType
    file_size_bytes: int
    s3_raw_key: str
    status: DocumentStatus = DocumentStatus.INGESTED
    error_message: str | None = None
    ingested_at: datetime = Field(default_factory=datetime.now)
    processed_at: datetime | None = None


class DocumentChunk(BaseModel):
    """A processed chunk of a document with its embedding."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    chunk_index: int
    chunk_text: str
    chunk_strategy: ChunkStrategy
    token_count: int
    embedding: list[float] | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
    pii_detected: bool = False
    pii_masked: bool = False


class PIIDetection(BaseModel):
    """Record of a PII entity detected in a document."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    chunk_id: UUID | None = None
    entity_type: PIIEntityType
    confidence: float
    original_text: str
    masked_text: str


# ── API Request/Response Models ──────────────────


class IngestRequest(BaseModel):
    """Request to ingest a new document."""

    filename: str
    source_domain: SourceDomain
    file_type: FileType


class IngestResponse(BaseModel):
    """Response after document ingestion."""

    document_id: UUID
    upload_url: str
    status: DocumentStatus = DocumentStatus.INGESTED


class QueryRequest(BaseModel):
    """Request to query the knowledge base."""

    query: str
    max_results: int = Field(default=5, ge=1, le=20)
    source_domains: list[SourceDomain] | None = None


class QueryResponse(BaseModel):
    """Response from the agentic RAG system."""

    answer: str
    sources: list["SourceReference"]
    query_rewritten: str | None = None
    intent: str | None = None
    latency_ms: int


class SourceReference(BaseModel):
    """A source document referenced in a query response."""

    document_id: UUID
    filename: str
    chunk_text: str
    relevance_score: float
    source_domain: SourceDomain


class HealthResponse(BaseModel):
    """API health check response."""

    status: str  # healthy | degraded | unhealthy
    version: str
    dependencies: dict[str, str]  # service_name -> status
