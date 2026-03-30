# C4 Level 3 — Component Diagram: Processing Layer

> Shows the internal components of the document processing pipeline.

```mermaid
graph TB
    KAFKA_IN["📨 Kafka: raw-documents"]

    subgraph Processing Pipeline
        CONSUMER["🔄 Kafka Consumer<br/><i>consumer.py</i><br/><br/>Reads document events,<br/>triggers pipeline per document"]

        subgraph Pipeline Orchestrator ["Pipeline Orchestrator (pipeline.py)"]
            S3DL["📥 S3 Downloader<br/><br/>Downloads raw document<br/>from S3 landing bucket"]

            PARSER["📄 Document Parser<br/><i>parser.py</i><br/><br/>Extracts text from<br/>TXT, CSV, JSON files.<br/>Handles malformed files."]

            CHUNKER["✂️ Text Chunker<br/><i>chunker.py</i><br/><br/>Splits text into ~500 token<br/>chunks with 50 token overlap.<br/>Breaks at sentence boundaries."]

            PII["🔒 PII Detector<br/><i>pii_detector.py</i><br/><br/>Presidio + custom AU recognizers.<br/>Detects: names, emails, phones,<br/>ABNs, Medicare, TFNs.<br/>Masks all detected PII."]

            EMBED["🧮 Embedding Generator<br/><i>embedder.py</i><br/><br/>Local: hash-based (dev, free).<br/>Bedrock: Titan Embed (prod).<br/>1024 dimensions per chunk."]

            STORE["💾 pgvector Writer<br/><br/>Stores chunks + embeddings<br/>in chunks table. Logs PII<br/>detections in audit table."]

            METRICS["📊 Quality Logger<br/><br/>Records processing metrics:<br/>chunks created, PII found,<br/>elapsed time, pass/fail."]
        end
    end

    PG["🗄️ PostgreSQL + pgvector"]
    S3["📦 S3 Data Lake"]

    KAFKA_IN -->|"Document event<br/>(id, filename, s3_key)"| CONSUMER
    CONSUMER -->|"Trigger pipeline"| S3DL
    S3DL -->|"Download raw file"| S3
    S3DL -->|"Raw bytes"| PARSER
    PARSER -->|"Extracted text"| CHUNKER
    CHUNKER -->|"Text chunks[]"| PII
    PII -->|"Masked chunks[]<br/>+ PII matches[]"| EMBED
    EMBED -->|"Chunks with embeddings[]"| STORE
    STORE -->|"INSERT chunks<br/>+ pii_detections"| PG
    METRICS -->|"INSERT quality_metrics"| PG

    CONSUMER -.->|"Update status<br/>processing → processed"| PG

    style CONSUMER fill:#1168bd,stroke:#0b4884,color:#ffffff
    style S3DL fill:#1168bd,stroke:#0b4884,color:#ffffff
    style PARSER fill:#1168bd,stroke:#0b4884,color:#ffffff
    style CHUNKER fill:#1168bd,stroke:#0b4884,color:#ffffff
    style PII fill:#d32f2f,stroke:#b71c1c,color:#ffffff
    style EMBED fill:#1168bd,stroke:#0b4884,color:#ffffff
    style STORE fill:#1168bd,stroke:#0b4884,color:#ffffff
    style METRICS fill:#1168bd,stroke:#0b4884,color:#ffffff
    style PG fill:#2e7d32,stroke:#1b5e20,color:#ffffff
    style S3 fill:#2e7d32,stroke:#1b5e20,color:#ffffff
    style KAFKA_IN fill:#e86d1a,stroke:#b85515,color:#ffffff
```

## Component Details

### Kafka Consumer (`consumer.py`)
- Subscribes to `raw-documents` topic
- Consumer group: `rippaa-processors`
- Auto-offset reset: `earliest` (processes all unread messages)
- Handles graceful shutdown via signal handlers
- Supports bounded mode (`--max-messages`) for testing

### Document Parser (`parser.py`)
- **TXT**: Returns content as-is
- **CSV**: Converts rows to `key: value | key: value` format. Handles malformed CSVs (extra columns, missing values) by skipping bad rows
- **JSON**: Recursively flattens nested structures into `path.to.key: value` format
- Raises `ParseError` for unrecoverable issues — pipeline catches and logs these

### Text Chunker (`chunker.py`)
- **Fixed-size strategy**: 500 tokens (~2000 chars) with 50 token overlap
- Break-point priority: sentence boundary > paragraph > newline > word > exact position
- Produces chunks with metadata: index, text, token count, character offsets
- Short documents (under chunk size) produce a single chunk

### PII Detector (`pii_detector.py`)
- **Presidio mode**: Uses AnalyzerEngine with custom Australian recognizers
- **Regex fallback**: Works when Presidio/spaCy models unavailable
- Custom entity types: `AU_ABN`, `AU_MEDICARE`, `AU_TFN`, `AU_PHONE`
- Confidence threshold: 0.7 (configurable)
- Masking: replaces PII with typed tokens (`[EMAIL_REDACTED]`, `[ABN_REDACTED]`, etc.)

### Embedding Generator (`embedder.py`)
- **Local mode**: Deterministic hash-based embeddings (SHA-512 → 1024 float vector). Free, fast, consistent. Not semantically meaningful — for pipeline testing only.
- **Bedrock mode**: Amazon Titan Embed Text v2. Production-quality semantic embeddings. 1024 dimensions.
- Mode selected via config: local for development, Bedrock for production

### pgvector Writer (in `pipeline.py`)
- Stores each chunk with its embedding in the `chunks` table
- Embedding stored as `vector(1024)` type with IVFFlat index for similarity search
- PII detections logged in `pii_detections` table with original and masked text
- Processing metrics logged in `quality_metrics` table

## Data Flow Summary

```
Document Event (Kafka)
    → Download from S3
    → Parse (TXT/CSV/JSON → plain text)
    → Chunk (500 tokens, 50 overlap, sentence breaks)
    → Detect PII (Presidio + AU recognizers)
    → Mask PII ([EMAIL_REDACTED], [ABN_REDACTED], ...)
    → Generate Embedding (local hash or Bedrock Titan)
    → Store in pgvector (chunks + embeddings + PII audit)
    → Log Quality Metrics (pass/fail, timing, counts)
```
