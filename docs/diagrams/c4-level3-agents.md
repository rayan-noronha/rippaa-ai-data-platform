# C4 Level 3 — Component Diagram: Intelligence Layer (Agentic RAG)

> Shows the internal components of the agentic RAG system.

```mermaid
graph TB
    API["🌐 FastAPI: POST /query"]

    subgraph Intelligence Layer
        ORCH["🎯 Orchestrator<br/><i>orchestrator.py</i><br/><br/>Coordinates agent pipeline.<br/>Handles errors, timing, logging."]

        subgraph Agent 1: Query Understanding
            QA["🧠 Query Agent<br/><i>query_agent.py</i><br/><br/>Classifies intent<br/>Rewrites query<br/>Selects search strategy<br/>Identifies source domains"]
        end

        subgraph Agent 2: Retrieval
            RA["🔍 Retrieval Agent<br/><i>retrieval_agent.py</i><br/><br/>Executes search strategy<br/>Returns ranked chunks"]

            subgraph Search Tools
                VS["📐 Vector Search<br/><i>pgvector cosine similarity</i>"]
                KS["📝 Keyword Search<br/><i>PostgreSQL full-text</i>"]
                HS["🔀 Hybrid Search<br/><i>RRF merge + re-rank</i>"]
            end
        end

        subgraph Agent 3: Data Quality
            DQA["✅ Quality Agent<br/><i>quality_agent.py</i><br/><br/>Checks source freshness<br/>Detects conflicts<br/>Flags stale documents<br/>Rates overall quality"]
        end

        subgraph Agent 4: Synthesis
            SA["💬 Synthesis Agent<br/><i>synthesis_agent.py</i><br/><br/>Generates answer from chunks<br/>Includes source citations<br/>Incorporates quality warnings"]
        end
    end

    PG["🗄️ PostgreSQL + pgvector"]
    LLM["🤖 Claude / Mock LLM<br/><i>llm_client.py</i>"]
    QLOG["📋 Query Log"]

    API -->|"Query + params"| ORCH

    ORCH -->|"1. Understand query"| QA
    QA -->|"Intent, strategy,<br/>rewritten query"| ORCH

    ORCH -->|"2. Retrieve chunks"| RA
    RA -->|"Select strategy"| HS
    HS -->|"Vector search"| VS
    HS -->|"Keyword search"| KS
    VS -->|"Cosine similarity"| PG
    KS -->|"Full-text search"| PG
    RA -->|"Ranked chunks"| ORCH

    ORCH -->|"3. Check quality"| DQA
    DQA -->|"Lookup metadata"| PG
    DQA -->|"Quality rating,<br/>warnings, conflicts"| ORCH

    ORCH -->|"4. Synthesise answer"| SA
    SA -->|"Answer + citations"| ORCH

    QA -->|"LLM call"| LLM
    DQA -->|"LLM call"| LLM
    SA -->|"LLM call"| LLM

    ORCH -->|"Log query + result"| QLOG

    style ORCH fill:#1168bd,stroke:#0b4884,color:#ffffff
    style QA fill:#7b1fa2,stroke:#4a148c,color:#ffffff
    style RA fill:#7b1fa2,stroke:#4a148c,color:#ffffff
    style DQA fill:#7b1fa2,stroke:#4a148c,color:#ffffff
    style SA fill:#7b1fa2,stroke:#4a148c,color:#ffffff
    style VS fill:#1565c0,stroke:#0d47a1,color:#ffffff
    style KS fill:#1565c0,stroke:#0d47a1,color:#ffffff
    style HS fill:#1565c0,stroke:#0d47a1,color:#ffffff
    style PG fill:#2e7d32,stroke:#1b5e20,color:#ffffff
    style LLM fill:#999999,stroke:#666666,color:#ffffff
    style QLOG fill:#2e7d32,stroke:#1b5e20,color:#ffffff
    style API fill:#e86d1a,stroke:#b85515,color:#ffffff
```

## Agent Pipeline Flow

```
User Query
    │
    ▼
┌─────────────────────────────────────────┐
│  Orchestrator                           │
│                                         │
│  1. Query Understanding Agent           │
│     ├── Classify intent                 │
│     ├── Rewrite query for retrieval     │
│     ├── Select strategy (hybrid/vector) │
│     └── Identify source domains         │
│                                         │
│  2. Retrieval Agent                     │
│     ├── Vector search (pgvector)        │
│     ├── Keyword search (full-text)      │
│     └── Hybrid merge (RRF re-ranking)   │
│                                         │
│  3. Data Quality Agent                  │
│     ├── Check source freshness          │
│     ├── Detect conflicting info         │
│     └── Rate overall quality            │
│                                         │
│  4. Synthesis Agent                     │
│     ├── Generate answer from chunks     │
│     ├── Include source citations        │
│     └── Add quality warnings            │
│                                         │
│  Log to query_log table                 │
└─────────────────────────────────────────┘
    │
    ▼
Answer + Sources + Metadata
```

## Component Details

### Orchestrator (`orchestrator.py`)
- Entry point: `run_query(query, max_results, source_domains)`
- Sequential execution with per-agent timing
- Error handling: if any agent fails, returns error response without crashing
- Logs complete query lifecycle to `query_log` table

### Query Understanding Agent (`query_agent.py`)
- Uses LLM to analyse the query
- Outputs: intent (information_retrieval, comparison, factual), rewritten query, search strategy (hybrid, vector, keyword), key terms, source domain suggestions
- In mock mode: returns sensible defaults without LLM call

### Retrieval Agent (`retrieval_agent.py`)
- Delegates to search tools based on strategy from query agent
- Hybrid mode: runs both vector and keyword search, merges with RRF
- Returns top N chunks with relevance scores

### Search Tools (`tools/search.py`)
- **Vector search**: pgvector cosine similarity with `<=>` operator
- **Keyword search**: PostgreSQL `to_tsvector` / `plainto_tsquery` with `ts_rank`
- **Hybrid search**: Reciprocal Rank Fusion (k=60, vector weight 0.6, keyword weight 0.4)

### Data Quality Agent (`quality_agent.py`)
- Checks each source document's ingestion date for freshness
- Uses LLM to detect conflicting information across chunks
- Rates overall quality: good, acceptable, or poor
- Returns warnings for stale or conflicting sources

### Synthesis Agent (`synthesis_agent.py`)
- Constructs prompt with query, chunks, and quality warnings
- LLM generates natural language answer with source citations
- In mock mode: returns template response summarising the retrieval

### LLM Client (`llm_client.py`)
- Abstraction layer for LLM calls
- Mock mode: returns template responses when no API key configured
- Production mode: calls Claude via Anthropic API or Bedrock
- All calls logged with timing
