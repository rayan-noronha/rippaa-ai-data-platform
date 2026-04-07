## Live Demo

Start the API locally and query the knowledge base:
```bash
make infra-up
make seed-data
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the claims process for insurance?", "max_results": 5}'
```

**Response:**
```json
{
  "query_id": "7bbac53b-0380-4a48-a150-0a7fb6839fee",
  "query": "What is the claims process for insurance?",
  "answer": "Based on the retrieved documents, here is a summary of the relevant information. The documents contain details about enterprise policies, procedures, and guidelines that relate to your query.",
  "sources": [
    {
      "document_id": "a190f29d-1327-48c4-9fb5-6c3ec0a242fd",
      "filename": "claims_report_q4_2025_011.csv",
      "source_domain": "insurance",
      "relevance_score": 0.9683
    }
  ],
  "metadata": {
    "intent": "information_retrieval",
    "search_strategy": "hybrid",
    "chunks_retrieved": 5,
    "quality": "acceptable",
    "quality_issues": [],
    "conflicts": []
  },
  "timing": {
    "query_understanding_ms": 2,
    "retrieval_ms": 141,
    "quality_check_ms": 29,
    "synthesis_ms": 3,
    "total_ms": 175
  }
}
```

The agentic pipeline runs four agents in sequence — query understanding, retrieval, quality assessment, and synthesis — completing end-to-end in **175ms** against 53 enterprise documents.

> **LLM modes:** Runs in mock mode by default (no cost). Set `RIPPAA_ANTHROPIC_API_KEY` in `.env` for real Claude responses, or configure `RIPPAA_LLM_PROVIDER=bedrock` for production AWS deployment.