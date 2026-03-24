# RIPPAA AI Data Platform

[![CI](https://github.com/rayan-noronha/rippaa-ai-data-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/rayan-noronha/rippaa-ai-data-platform/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Production-grade AI data platform that ingests unstructured enterprise documents, processes them at scale, and exposes intelligent retrieval via RAG and agentic workflows — all on AWS.

---

## The Problem

Enterprises sit on massive volumes of unstructured data — policy documents, claims reports, compliance filings, internal memos. Teams waste hours manually searching, cross-referencing, and extracting insights. Existing search tools return keyword matches, not answers.

## The Solution

This platform provides an end-to-end pipeline that:

1. **Ingests** documents (PDF, CSV, JSON) into S3 with validation and event-driven routing
2. **Processes** them at scale using PySpark — parsing, chunking, PII detection, and embedding generation
3. **Stores** embeddings in pgvector with full metadata and lineage tracking
4. **Retrieves** intelligently using an agentic architecture with hybrid search (vector + keyword), query understanding, and source-cited answer synthesis
5. **Governs** data quality with automated freshness checks, drift detection, and conflict flagging

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  INGESTION          S3 Landing → Lambda → Kafka (MSK)        │
├──────────────────────────────────────────────────────────────┤
│  PROCESSING         PySpark (Glue/EMR) → Parse → Chunk →     │
│                     PII Mask → Embed → Kafka                  │
├──────────────────────────────────────────────────────────────┤
│  STORAGE            pgvector (RDS) + S3 Data Lake + Metadata │
├──────────────────────────────────────────────────────────────┤
│  INTELLIGENCE       Agentic RAG: Query → Retrieve → Synthesise│
│                     + Data Quality Agent                      │
├──────────────────────────────────────────────────────────────┤
│  SERVING            FastAPI on ECS Fargate + Prometheus/Grafana│
└──────────────────────────────────────────────────────────────┘
```

> Detailed C4 architecture diagrams available in [`docs/diagrams/`](docs/diagrams/)

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.12 | Universal across enterprise data roles |
| Streaming | Amazon MSK (Kafka) | Event-driven, decoupled, scalable |
| Processing | PySpark on Glue/EMR Serverless | Handles large-scale document processing |
| Vector DB | pgvector (PostgreSQL) | No vendor lock-in, cost-effective |
| LLM | Claude via Amazon Bedrock | Production-grade, enterprise-ready |
| API | FastAPI | Async-native, auto-documented |
| PII Detection | Presidio + AWS Comprehend | Compliance-ready for regulated industries |
| IaC | Terraform | Multi-cloud, declarative, auditable |
| Containers | Docker + ECS Fargate | Serverless compute, no cluster management |
| CI/CD | GitHub Actions | Integrated with repo, free for public repos |
| Observability | CloudWatch + Prometheus + Grafana | Full-stack monitoring |

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Make
- AWS CLI (configured, for deployment only)

### Local Development

```bash
# Clone the repo
git clone https://github.com/rayan-noronha/rippaa-ai-data-platform.git
cd rippaa-ai-data-platform

# Set up Python environment
make setup

# Start local infrastructure (Kafka, PostgreSQL + pgvector, LocalStack)
make infra-up

# Generate synthetic test documents
make seed-data

# Run the full pipeline locally
make run

# Run tests
make test

# Run linting
make lint

# Stop local infrastructure
make infra-down
```

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest` | Submit documents for processing |
| `POST` | `/query` | Ask questions against the knowledge base |
| `GET` | `/documents` | List ingested documents and their status |
| `GET` | `/health` | Service health check with dependency status |
| `GET` | `/metrics` | Prometheus metrics endpoint |

## Project Structure

```
rippaa-ai-data-platform/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RUNBOOK.md
│   ├── DATA_DICTIONARY.md
│   ├── adr/                         # Architecture Decision Records
│   └── diagrams/                    # C4 model diagrams (Excalidraw)
├── infrastructure/
│   ├── terraform/                   # AWS infrastructure as code
│   └── docker/
│       └── docker-compose.yml       # Local dev environment
├── src/
│   ├── ingestion/                   # S3 event → validation → Kafka
│   ├── processing/                  # PySpark document processing
│   │   └── spark_jobs/
│   ├── agents/                      # Agentic RAG system
│   │   └── tools/                   # Agent tool implementations
│   ├── api/                         # FastAPI service
│   └── shared/                      # Config, models, DB utilities
├── scripts/
│   ├── seed_data.py                 # Synthetic data generator
│   └── run_demo.py                  # End-to-end demo
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── Makefile
└── .pre-commit-config.yaml
```

## Architecture Decision Records

All major technical decisions are documented as ADRs in [`docs/adr/`](docs/adr/):

| ADR | Decision | Status |
|---|---|---|
| [001](docs/adr/001-pgvector-over-pinecone.md) | pgvector over Pinecone for vector storage | Accepted |
| [002](docs/adr/002-kafka-over-sqs.md) | Kafka (MSK) over SQS for event streaming | Accepted |
| [003](docs/adr/003-pyspark-over-pandas.md) | PySpark over pandas for document processing | Accepted |
| [004](docs/adr/004-claude-bedrock-over-openai.md) | Claude/Bedrock over OpenAI for LLM | Accepted |
| [005](docs/adr/005-fastapi-over-flask.md) | FastAPI over Flask for API layer | Accepted |
| [006](docs/adr/006-terraform-over-cdk.md) | Terraform over CDK/CloudFormation | Accepted |
| [007](docs/adr/007-hybrid-search-strategy.md) | Hybrid search (vector + keyword) over pure vector | Accepted |
| [008](docs/adr/008-agent-tool-use-pattern.md) | Agent tool-use pattern over chain-based orchestration | Accepted |
| [009](docs/adr/009-chunking-strategy.md) | Chunking strategy selection | Accepted |
| [010](docs/adr/010-pii-detection-approach.md) | PII detection with Presidio + Comprehend | Accepted |

## Data Quality

This platform intentionally handles messy, enterprise-grade data:

- **PII Detection & Masking** — Catches names, emails, ABNs, Medicare numbers embedded in documents
- **Duplicate Detection** — Identifies re-ingested documents with variant metadata
- **Schema Validation** — Flags missing fields, format inconsistencies
- **Source Freshness** — Alerts on stale documents that may contain outdated information
- **Conflict Detection** — Identifies contradictory information across documents

## Cost

Designed for cost-conscious enterprises. Local development runs entirely on Docker (free). AWS deployment targets ~$50–70/month during development using:

- LocalStack for S3 emulation during dev
- RDS db.t3.micro for PostgreSQL
- MSK Serverless for Kafka
- ECS Fargate with minimal task sizing

See [ADR-001](docs/adr/001-pgvector-over-pinecone.md) for the cost-optimisation rationale behind key infrastructure decisions.

## License

MIT — see [LICENSE](LICENSE) for details.

## Author

**Rayan Noronha** — Data & AI Platform Engineer | Adelaide, Australia

- Website: [rippaa.com](https://rippaa.com)
- LinkedIn: [linkedin.com/in/rayannoronha](https://linkedin.com/in/rayannoronha)
- GitHub: [github.com/rayan-noronha](https://github.com/rayan-noronha)
