"""RIPPAA AI Data Platform — FastAPI application."""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from src.shared.config import get_settings
from src.shared.database import check_database_health
from src.shared.models import HealthResponse

logger = structlog.get_logger(__name__)

# ── Prometheus Metrics ───────────────────────────

REQUEST_COUNT = Counter(
    "rippaa_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "rippaa_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)

DOCUMENTS_INGESTED = Counter(
    "rippaa_documents_ingested_total",
    "Total documents ingested",
    ["source_domain"],
)

QUERIES_PROCESSED = Counter(
    "rippaa_queries_processed_total",
    "Total queries processed",
)


# ── Application Lifecycle ────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown logic."""
    settings = get_settings()
    logger.info("Starting RIPPAA AI Data Platform", version=settings.app_version, environment=settings.environment)
    yield
    logger.info("Shutting down RIPPAA AI Data Platform")


# ── App Factory ──────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="RIPPAA AI Data Platform",
    description="Production-grade AI data platform with RAG & agentic workflows",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware ────────────────────────────────────


@app.middleware("http")
async def metrics_middleware(request: Request, call_next: object) -> Response:
    """Track request count and latency for Prometheus."""
    start_time = time.perf_counter()
    response = await call_next(request)  # type: ignore[misc]
    latency = time.perf_counter() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(latency)

    return response  # type: ignore[return-value]


# ── Routes ───────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check service health and dependency status."""
    db_healthy = check_database_health()

    dependencies = {
        "postgres": "healthy" if db_healthy else "unhealthy",
        "kafka": "unknown",  # TODO: Implement Kafka health check
        "s3": "unknown",  # TODO: Implement S3 health check
    }

    overall = "healthy" if db_healthy else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        dependencies=dependencies,
    )


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.post("/ingest")
async def ingest_document() -> dict[str, str]:
    """Submit a document for processing."""
    # TODO: Implement in Phase 1
    return {"status": "not_implemented", "message": "Document ingestion coming in Phase 1"}


@app.post("/query")
async def query_knowledge_base() -> dict[str, str]:
    """Query the knowledge base using agentic RAG."""
    # TODO: Implement in Phase 3
    return {"status": "not_implemented", "message": "Agentic RAG query coming in Phase 3"}


@app.get("/documents")
async def list_documents() -> dict[str, str]:
    """List all ingested documents and their processing status."""
    # TODO: Implement in Phase 1
    return {"status": "not_implemented", "message": "Document listing coming in Phase 1"}
