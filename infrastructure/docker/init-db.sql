-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────
-- Document Registry
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename        VARCHAR(500) NOT NULL,
    source_domain   VARCHAR(100) NOT NULL,  -- insurance, financial, government, enterprise
    file_type       VARCHAR(20) NOT NULL,   -- pdf, csv, json, txt, docx
    file_size_bytes BIGINT NOT NULL,
    s3_raw_key      VARCHAR(1000) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'ingested',  -- ingested, processing, processed, failed
    error_message   TEXT,
    ingested_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at    TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_domain ON documents(source_domain);

-- ─────────────────────────────────────────────
-- Document Chunks with Embeddings
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    chunk_text      TEXT NOT NULL,
    chunk_strategy  VARCHAR(50) NOT NULL,   -- fixed_size, semantic, sliding_window
    token_count     INTEGER NOT NULL,
    embedding       vector(1024),           -- Claude/Bedrock embedding dimension
    metadata        JSONB DEFAULT '{}',
    pii_detected    BOOLEAN DEFAULT FALSE,
    pii_masked      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─────────────────────────────────────────────
-- PII Detection Log
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pii_detections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id        UUID REFERENCES chunks(id) ON DELETE CASCADE,
    entity_type     VARCHAR(50) NOT NULL,   -- PERSON, EMAIL, PHONE, ABN, MEDICARE
    confidence      FLOAT NOT NULL,
    original_text   VARCHAR(500),           -- Stored only for audit, masked in responses
    masked_text     VARCHAR(500),
    detected_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pii_document ON pii_detections(document_id);

-- ─────────────────────────────────────────────
-- Data Quality Metrics
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quality_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID REFERENCES documents(id) ON DELETE CASCADE,
    metric_type         VARCHAR(50) NOT NULL,   -- ingestion, processing, embedding, pii_scan
    status              VARCHAR(20) NOT NULL,   -- pass, fail, warning
    details             JSONB DEFAULT '{}',
    measured_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_quality_document ON quality_metrics(document_id);
CREATE INDEX idx_quality_type ON quality_metrics(metric_type);

-- ─────────────────────────────────────────────
-- Query Audit Log
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS query_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text          TEXT NOT NULL,
    rewritten_query     TEXT,
    intent              VARCHAR(50),
    retrieval_strategy  VARCHAR(50),
    chunks_retrieved    INTEGER,
    response_text       TEXT,
    latency_ms          INTEGER,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
