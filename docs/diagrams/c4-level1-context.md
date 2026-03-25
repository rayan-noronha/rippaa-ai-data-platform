# C4 Level 1 — System Context Diagram

> Shows the RIPPAA AI Data Platform as a whole and how it interacts with external actors.

```mermaid
graph TB
    subgraph External Actors
        DU["👤 Document Uploaders<br/><i>Business users or automated systems<br/>that submit enterprise documents</i>"]
        KC["👤 Knowledge Consumers<br/><i>Applications or users querying<br/>the knowledge base for answers</i>"]
        MS["🖥️ Monitoring Team<br/><i>Engineers monitoring system<br/>health and performance</i>"]
    end

    RIPPAA["🏢 RIPPAA AI Data Platform<br/><br/><i>Ingests unstructured enterprise documents,<br/>processes them into a searchable knowledge base,<br/>and provides intelligent retrieval via<br/>agentic RAG workflows</i>"]

    subgraph External Services
        LLM["🤖 Claude via Amazon Bedrock<br/><i>LLM for embedding generation<br/>and answer synthesis</i>"]
        S3["☁️ Amazon S3<br/><i>Raw document storage<br/>and processed data lake</i>"]
    end

    DU -->|"Upload documents<br/>(PDF, CSV, JSON, TXT)"| RIPPAA
    KC -->|"Ask questions,<br/>receive cited answers"| RIPPAA
    MS -->|"View dashboards,<br/>receive alerts"| RIPPAA

    RIPPAA -->|"Generate embeddings,<br/>synthesise answers"| LLM
    RIPPAA -->|"Store raw documents,<br/>read for processing"| S3

    style RIPPAA fill:#1168bd,stroke:#0b4884,color:#ffffff
    style DU fill:#08427b,stroke:#052e56,color:#ffffff
    style KC fill:#08427b,stroke:#052e56,color:#ffffff
    style MS fill:#08427b,stroke:#052e56,color:#ffffff
    style LLM fill:#999999,stroke:#666666,color:#ffffff
    style S3 fill:#999999,stroke:#666666,color:#ffffff
```

## Description

The RIPPAA AI Data Platform is an enterprise data system that:

1. **Receives** unstructured documents from business users or automated systems across four domains: insurance, financial services, government, and enterprise
2. **Processes** them through a pipeline that parses, chunks, detects PII, and generates vector embeddings
3. **Stores** the processed data in a searchable knowledge base
4. **Answers** questions from knowledge consumers using an agentic RAG system that retrieves relevant information and synthesises cited answers
5. **Reports** system health, performance metrics, and data quality to the monitoring team

External dependencies:
- **Claude via Amazon Bedrock** — Provides LLM capabilities for embedding generation and answer synthesis
- **Amazon S3** — Persistent storage for raw documents and processed data
