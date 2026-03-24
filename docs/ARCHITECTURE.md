# Architecture Overview

> This document provides a holistic view of the RIPPAA AI Data Platform architecture. For individual technology decisions, see the [Architecture Decision Records](adr/).

## System Context (C4 Level 1)

The RIPPAA AI Data Platform is an enterprise data system that ingests unstructured documents from multiple business domains (insurance, financial services, government, enterprise), processes them into a searchable knowledge base, and provides intelligent retrieval via an agentic RAG system.

**External actors:**
- **Document Uploaders** — Business users or automated systems that submit documents via the API or S3
- **Knowledge Consumers** — Applications or users that query the platform for answers
- **LLM Provider** — Claude via Amazon Bedrock, used for embedding generation and answer synthesis
- **Monitoring Systems** — Prometheus + Grafana for observability

## Container View (C4 Level 2)

### Ingestion Layer
- **S3 Landing Zone** — Raw documents land here (via API upload or direct S3 put)
- **Lambda Validator** — Triggered by S3 events, validates file type/size, extracts metadata, produces to Kafka
- **Kafka `raw-documents` topic** — Decouples ingestion from processing, enables replay

### Processing Layer
- **PySpark Jobs** (Glue/EMR Serverless) — Consume from Kafka, process documents through:
  1. Document parsing (PDF → text, CSV → structured data, JSON → normalised)
  2. Chunking (configurable strategy: fixed-size, semantic, sliding window)
  3. PII detection and masking (Presidio + AWS Comprehend)
  4. Embedding generation (Amazon Bedrock Titan embeddings)
- **Kafka `processed-chunks` topic** — Carries processed chunks to storage layer

### Storage Layer
- **pgvector (PostgreSQL on RDS)** — Stores document embeddings, metadata, chunk text, and audit logs in a single database ([ADR-001](adr/001-pgvector-over-pinecone.md))
- **S3 Data Lake** — Raw documents, processed Parquet files, and lineage logs
- **Tables:** `documents`, `chunks`, `pii_detections`, `quality_metrics`, `query_log`

### Intelligence Layer
- **Agent Orchestrator** — Coordinates the agentic RAG workflow using a tool-use pattern
- **Query Understanding Agent** — Classifies intent, rewrites queries for better retrieval
- **Retrieval Agent** — Executes hybrid search (vector cosine similarity + keyword matching), re-ranks results
- **Synthesis Agent** — Generates answers using Claude with source citations
- **Data Quality Agent** — Validates source freshness, detects drift, flags conflicting information

### Serving Layer
- **FastAPI** — REST API on ECS Fargate, exposes `/ingest`, `/query`, `/documents`, `/health`, `/metrics`
- **Prometheus + Grafana** — Full-stack observability

## Data Flow

```
Document Upload
      │
      ▼
S3 Landing Zone ──► Lambda (validate) ──► Kafka [raw-documents]
                                                │
                                                ▼
                                    PySpark Processing Pipeline
                                    ├── Parse document
                                    ├── Chunk text
                                    ├── Detect & mask PII
                                    └── Generate embeddings
                                                │
                                                ▼
                                    Kafka [processed-chunks]
                                                │
                                                ▼
                              ┌──────────────────┴──────────────────┐
                              │                                     │
                         pgvector                              S3 Data Lake
                    (embeddings + metadata)               (raw + processed files)
                              │
                              ▼
                    Query via FastAPI /query
                              │
                              ▼
                    Agent Orchestrator
                    ├── Query Understanding Agent
                    ├── Retrieval Agent (hybrid search)
                    ├── Data Quality Agent (validation)
                    └── Synthesis Agent (answer + citations)
                              │
                              ▼
                    JSON Response with answer + sources
```

## Key Design Principles

1. **Cost-conscious by default.** Every infrastructure decision considers cost alongside capability. See ADRs for trade-off analysis.
2. **Observable from day one.** Structured logging, Prometheus metrics, and health checks are built into every component — not added as an afterthought.
3. **Governance is a feature, not an audit.** PII detection, data quality checks, and query audit logging are core pipeline stages, not bolt-ons.
4. **Replay-friendly.** Kafka retention + idempotent processing means we can reprocess any document at any time without re-ingestion.
5. **Local-first development.** Docker Compose provides a complete local environment (Kafka, PostgreSQL, S3 via LocalStack) — no AWS account needed for development.

## Security Considerations

- No secrets in code — all credentials via environment variables or AWS Secrets Manager
- PII is masked before storage — raw PII is logged only in the `pii_detections` audit table
- API rate limiting and input validation on all endpoints
- Bandit security linting in CI pipeline
- Non-root Docker containers

## Diagrams

Detailed C4 diagrams are in [`diagrams/`](diagrams/). Created with Excalidraw for clean, editable architecture visuals.
