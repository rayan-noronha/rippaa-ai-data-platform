# ADR-008: Agent Tool-Use Pattern over Chain-Based Orchestration

## Status

Accepted

## Date

2026-03-31

## Context

The intelligence layer needs to orchestrate multiple steps: query understanding, retrieval, data quality checking, and answer synthesis. Two main patterns exist:

1. **Chain-based** — Fixed sequence of steps (LangChain-style): query → retrieve → synthesise. Every query follows the same path.
2. **Agent tool-use** — Agents have access to tools and decide which to use based on the query. More flexible, can skip steps or loop.

## Decision

We use an **agent tool-use pattern** with four specialised agents orchestrated by a central controller.

## Rationale

### Why agents over chains
- **Flexibility**: Not every query needs the same processing. A simple factual query doesn't need data quality checks. A complex comparison query might need multiple retrieval passes. Agents can adapt.
- **Extensibility**: Adding a new capability (e.g., a summarisation tool, a calculator) means adding a tool, not rewriting the chain.
- **Transparency**: Each agent logs its reasoning and actions, creating an auditable trace of how an answer was produced.
- **Employer alignment**: "Agentic AI" appears in 5 of 7 target job descriptions. Demonstrating agent architecture is a direct signal.

### Our four agents

**Query Understanding Agent**
- Input: Raw user query
- Output: Intent classification, rewritten query, search strategy, key terms, source domain filter
- Tools: LLM (Claude) for intent analysis
- Why separate: Determines the entire downstream strategy. A well-rewritten query dramatically improves retrieval quality.

**Retrieval Agent**
- Input: Rewritten query, search strategy, domain filter
- Output: Ranked list of relevant chunks
- Tools: Vector search, keyword search, hybrid search
- Why separate: Encapsulates all search logic. Can switch strategies (vector-only, keyword-only, hybrid) based on query understanding output.

**Data Quality Agent**
- Input: Retrieved chunks
- Output: Quality assessment, conflict flags, freshness warnings
- Tools: Document metadata lookup, LLM for conflict detection
- Why separate: Quality checking is independent of retrieval. Can be enhanced (e.g., cross-reference checking) without touching search logic.

**Synthesis Agent**
- Input: Query, retrieved chunks, quality assessment
- Output: Natural language answer with source citations
- Tools: LLM (Claude) for answer generation
- Why separate: Answer generation is the most LLM-intensive step. Isolating it allows independent optimisation (prompt tuning, model selection, caching).

### Orchestration pattern
- Sequential with early termination: Query → Understand → Retrieve → Quality Check → Synthesise
- If retrieval returns zero results, skip quality check and synthesis, return "no results found"
- If quality check finds critical issues, include warnings in the synthesis prompt
- Total pipeline logged to `query_log` table with per-agent timing

### Trade-offs accepted
- More complex than a simple chain — four agents instead of one linear pipeline
- Each agent adds latency (though agents 1 and 4 are <10ms in mock mode)
- In mock mode (no API key), LLM calls return template responses — full quality requires Claude API access

## Consequences

- Each agent is a separate module in `src/agents/` — independently testable and deployable
- The orchestrator (`orchestrator.py`) coordinates agents and handles errors
- Adding new agents (e.g., a follow-up question agent) requires minimal changes to the orchestrator
- Per-agent timing is tracked and logged — easy to identify bottlenecks
- Query audit trail includes intent, strategy, chunk count, and quality assessment

## References

- [ReAct pattern](https://arxiv.org/abs/2210.03629)
- [Tool-use in LLM agents](https://lilianweng.github.io/posts/2023-06-23-agent/)
