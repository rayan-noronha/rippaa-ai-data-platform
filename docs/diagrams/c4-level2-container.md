# C4 Level 2 — Container Diagram

> Shows the major containers (services, data stores, applications) within the RIPPAA AI Data Platform.

```mermaid
graph TB
    DU["👤 Document Uploaders"]
    KC["👤 Knowledge Consumers"]

    subgraph RIPPAA AI Data Platform
        subgraph Ingestion Layer
            API["🌐 FastAPI Service<br/><i>Python / ECS Fargate</i><br/><br/>REST API for document upload,<br/>queries, health, and metrics"]
            LAMBDA["⚡ Ingestion Handler<br/><i>Python</i><br/><br/>Validates documents, extracts<br/>metadata, publishes to Kafka"]
        end

        subgraph Streaming Layer
            KAFKA_RAW["📨 Kafka: raw-documents<br/><i>Amazon MSK</i><br/><br/>Events for newly ingested<br/>documents awaiting processing"]
            KAFKA_PROC["📨 Kafka: processed-chunks<br/><i>Amazon MSK</i><br/><br/>Processed chunks ready<br/>for storage"]
        end

        subgraph Processing Layer
            SPARK["⚙️ PySpark Processing<br/><i>AWS Glue / EMR Serverless</i><br/><br/>Document parsing, chunking,<br/>PII detection, embedding generation"]
        end

        subgraph Intelligence Layer
            AGENTS["🤖 Agentic RAG System<br/><i>Python</i><br/><br/>Query understanding, hybrid retrieval,<br/>data quality checks, answer synthesis"]
        end

        subgraph Storage Layer
            PG["🗄️ PostgreSQL + pgvector<br/><i>Amazon RDS</i><br/><br/>Document registry, embeddings,<br/>PII audit log, query log"]
            S3_STORE["📦 S3 Data Lake<br/><i>Amazon S3</i><br/><br/>Raw documents, processed<br/>Parquet files, lineage logs"]
        end

        subgraph Observability
            PROM["📊 Prometheus<br/><i>Metrics collection</i>"]
            GRAF["📈 Grafana<br/><i>Dashboards & alerts</i>"]
        end
    end

    LLM["🤖 Claude via Bedrock<br/><i>External LLM service</i>"]

    %% Document Upload Flow
    DU -->|"POST /ingest"| API
    API -->|"Validate & route"| LAMBDA
    LAMBDA -->|"Upload raw file"| S3_STORE
    LAMBDA -->|"Register metadata"| PG
    LAMBDA -->|"Publish event"| KAFKA_RAW

    %% Processing Flow
    KAFKA_RAW -->|"Consume events"| SPARK
    SPARK -->|"Generate embeddings"| LLM
    SPARK -->|"Publish chunks"| KAFKA_PROC
    KAFKA_PROC -->|"Store embeddings"| PG
    KAFKA_PROC -->|"Store Parquet"| S3_STORE

    %% Query Flow
    KC -->|"POST /query"| API
    API -->|"Route to agents"| AGENTS
    AGENTS -->|"Hybrid search"| PG
    AGENTS -->|"Synthesise answer"| LLM
    AGENTS -->|"Return cited answer"| API

    %% Observability
    API -->|"Expose /metrics"| PROM
    PROM -->|"Visualise"| GRAF

    style API fill:#1168bd,stroke:#0b4884,color:#ffffff
    style LAMBDA fill:#1168bd,stroke:#0b4884,color:#ffffff
    style SPARK fill:#1168bd,stroke:#0b4884,color:#ffffff
    style AGENTS fill:#1168bd,stroke:#0b4884,color:#ffffff
    style KAFKA_RAW fill:#e86d1a,stroke:#b85515,color:#ffffff
    style KAFKA_PROC fill:#e86d1a,stroke:#b85515,color:#ffffff
    style PG fill:#2e7d32,stroke:#1b5e20,color:#ffffff
    style S3_STORE fill:#2e7d32,stroke:#1b5e20,color:#ffffff
    style PROM fill:#666666,stroke:#444444,color:#ffffff
    style GRAF fill:#666666,stroke:#444444,color:#ffffff
    style LLM fill:#999999,stroke:#666666,color:#ffffff
    style DU fill:#08427b,stroke:#052e56,color:#ffffff
    style KC fill:#08427b,stroke:#052e56,color:#ffffff
```

## Data Flows

### 1. Document Ingestion Flow
1. Document Uploaders submit files via `POST /ingest` to the FastAPI service
2. The Ingestion Handler validates the file, uploads it to S3, registers metadata in PostgreSQL
3. An event is published to the `raw-documents` Kafka topic

### 2. Document Processing Flow
1. PySpark jobs consume events from `raw-documents`
2. For each document: parse → chunk → detect PII → generate embeddings (via Claude/Bedrock)
3. Processed chunks are published to `processed-chunks` Kafka topic
4. A consumer stores embeddings in pgvector and processed files in S3

### 3. Query Flow
1. Knowledge Consumers submit questions via `POST /query`
2. The Agentic RAG system orchestrates four agents:
   - **Query Understanding Agent** — Classifies intent and rewrites the query
   - **Retrieval Agent** — Executes hybrid search (vector + keyword) against pgvector
   - **Data Quality Agent** — Validates source freshness and detects conflicts
   - **Synthesis Agent** — Generates a cited answer using Claude
3. The response is returned with source references

### 4. Observability Flow
1. FastAPI exposes Prometheus metrics at `/metrics`
2. Prometheus scrapes metrics every 15 seconds
3. Grafana dashboards visualise request latency, throughput, and system health

## Container Technologies

| Container | Technology | Deployment |
|---|---|---|
| FastAPI Service | Python 3.12, FastAPI, Uvicorn | ECS Fargate |
| Ingestion Handler | Python 3.12 | Part of API service (Phase 1) |
| Kafka Topics | Apache Kafka | Amazon MSK Serverless |
| PySpark Processing | PySpark 3.5 | AWS Glue / EMR Serverless |
| Agentic RAG System | Python 3.12, Claude API | Part of API service |
| PostgreSQL + pgvector | PostgreSQL 16, pgvector | Amazon RDS |
| S3 Data Lake | Amazon S3 | AWS S3 |
| Prometheus | Prometheus | Self-hosted / Amazon Managed Prometheus |
| Grafana | Grafana | Self-hosted / Amazon Managed Grafana |
