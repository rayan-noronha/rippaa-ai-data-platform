# Data Dictionary

> Schema definitions for all persistent data entities in the RIPPAA AI Data Platform.

## PostgreSQL Tables

### `documents`

The document registry — tracks every file ingested into the platform.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | UUID | No | Primary key, auto-generated |
| filename | VARCHAR(500) | No | Original filename |
| source_domain | VARCHAR(100) | No | Industry domain: insurance, financial, government, enterprise |
| file_type | VARCHAR(20) | No | File format: pdf, csv, json, txt, docx |
| file_size_bytes | BIGINT | No | File size in bytes |
| s3_raw_key | VARCHAR(1000) | No | S3 key for the raw document in the landing bucket |
| status | VARCHAR(20) | No | Lifecycle: ingested → processing → processed / failed |
| error_message | TEXT | Yes | Error details if status = failed |
| ingested_at | TIMESTAMPTZ | No | When the document was received |
| processed_at | TIMESTAMPTZ | Yes | When processing completed |
| created_at | TIMESTAMPTZ | No | Row creation time |
| updated_at | TIMESTAMPTZ | No | Last update time |

### `chunks`

Document chunks with embeddings — the core data structure for RAG retrieval.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | UUID | No | Primary key, auto-generated |
| document_id | UUID (FK) | No | References `documents.id` |
| chunk_index | INTEGER | No | Position within the document (0-based) |
| chunk_text | TEXT | No | The text content of this chunk |
| chunk_strategy | VARCHAR(50) | No | Strategy used: fixed_size, semantic, sliding_window |
| token_count | INTEGER | No | Token count for the chunk text |
| embedding | vector(1024) | Yes | Embedding vector (null until embedding job runs) |
| metadata | JSONB | No | Additional metadata (page number, section title, etc.) |
| pii_detected | BOOLEAN | No | Whether PII was detected in this chunk |
| pii_masked | BOOLEAN | No | Whether PII has been masked |
| created_at | TIMESTAMPTZ | No | Row creation time |

### `pii_detections`

Audit log of all PII entities detected during document processing.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | UUID | No | Primary key, auto-generated |
| document_id | UUID (FK) | No | References `documents.id` |
| chunk_id | UUID (FK) | Yes | References `chunks.id` (null if detected at document level) |
| entity_type | VARCHAR(50) | No | PII type: PERSON, EMAIL, PHONE, ABN, MEDICARE, ADDRESS, DATE_OF_BIRTH, CREDIT_CARD |
| confidence | FLOAT | No | Detection confidence score (0.0–1.0) |
| original_text | VARCHAR(500) | Yes | Original PII text (stored for audit only) |
| masked_text | VARCHAR(500) | Yes | Masked replacement text |
| detected_at | TIMESTAMPTZ | No | When detection occurred |

### `quality_metrics`

Data quality measurements recorded during pipeline processing.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | UUID | No | Primary key, auto-generated |
| document_id | UUID (FK) | Yes | References `documents.id` |
| metric_type | VARCHAR(50) | No | Stage: ingestion, processing, embedding, pii_scan |
| status | VARCHAR(20) | No | Result: pass, fail, warning |
| details | JSONB | No | Metric-specific details (error counts, durations, etc.) |
| measured_at | TIMESTAMPTZ | No | When the metric was recorded |

### `query_log`

Audit log of all queries made against the knowledge base.

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | UUID | No | Primary key, auto-generated |
| query_text | TEXT | No | Original user query |
| rewritten_query | TEXT | Yes | Query after agent rewriting |
| intent | VARCHAR(50) | Yes | Classified query intent |
| retrieval_strategy | VARCHAR(50) | Yes | Strategy used: vector, keyword, hybrid |
| chunks_retrieved | INTEGER | Yes | Number of chunks retrieved |
| response_text | TEXT | Yes | Generated answer |
| latency_ms | INTEGER | Yes | Total query processing time in milliseconds |
| created_at | TIMESTAMPTZ | No | When the query was made |

## Kafka Topics

### `raw-documents`

| Field | Type | Description |
|---|---|---|
| document_id | string (UUID) | Unique document identifier |
| filename | string | Original filename |
| source_domain | string | Industry domain |
| file_type | string | File format |
| s3_key | string | S3 location of the raw file |
| ingested_at | string (ISO 8601) | Ingestion timestamp |

### `processed-chunks`

| Field | Type | Description |
|---|---|---|
| chunk_id | string (UUID) | Unique chunk identifier |
| document_id | string (UUID) | Parent document identifier |
| chunk_index | integer | Position within document |
| chunk_text | string | Processed chunk text (PII masked) |
| embedding | array[float] | 1024-dimension embedding vector |
| token_count | integer | Token count |
| metadata | object | Additional metadata |

## S3 Buckets

### `rippaa-landing`

Raw documents as uploaded. Structure: `{source_domain}/{YYYY}/{MM}/{DD}/{document_id}/{filename}`

### `rippaa-processed`

Processed outputs in Parquet format. Structure: `chunks/{document_id}/chunks.parquet`
