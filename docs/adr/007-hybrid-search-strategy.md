# ADR-007: Hybrid Search (Vector + Keyword) over Pure Vector Search

## Status

Accepted

## Date

2026-03-31

## Context

The RAG retrieval layer needs to find the most relevant document chunks for a given query. Options:

1. **Pure vector search** — Cosine similarity against pgvector embeddings only
2. **Pure keyword search** — PostgreSQL full-text search (tsvector/tsquery) only
3. **Hybrid search** — Combine both with re-ranking

Key challenge: Our embeddings are generated locally using hash-based approximation (not semantic). Even with production Bedrock embeddings, vector search alone misses exact-term matches, and keyword search alone misses semantic similarity.

## Decision

We use **hybrid search** with Reciprocal Rank Fusion (RRF) to merge results from vector and keyword search.

## Rationale

### Why hybrid beats either alone
- **Vector search** finds semantically similar content but misses exact terms. Query "CPS 234 compliance" might not match a chunk containing "CPS 234" if the embedding model doesn't weight regulatory codes heavily.
- **Keyword search** finds exact term matches but misses semantic meaning. Query "insurance claim process" won't find a chunk about "lodging a claim and assessment procedure" despite meaning the same thing.
- **Hybrid** catches both — exact terms AND semantic meaning. Research consistently shows hybrid outperforms either alone by 5-15% on retrieval benchmarks.

### Reciprocal Rank Fusion (RRF)
- Simple, effective merging algorithm: `score = Σ(1 / (k + rank))` for each result across both search methods
- No training required — works out of the box
- k=60 (standard) dampens the impact of rank position
- Weighted: vector results get 0.6 weight, keyword results get 0.4 weight (tunable)
- De-duplicates chunks that appear in both result sets

### Implementation
- Vector search: pgvector cosine similarity (`<=>` operator) with IVFFlat index
- Keyword search: PostgreSQL `to_tsvector` / `plainto_tsquery` with `ts_rank`
- Each returns top 2N results (where N is the desired final count)
- RRF merges, de-duplicates, and returns top N

### Our results
- For query "What is the claims process for insurance?": vector found 10 results, keyword found 9, hybrid merged to top 5
- Total retrieval time: ~654ms (acceptable for interactive queries)

## Consequences

- Two database queries per search (vector + keyword) — slightly more DB load than pure vector
- RRF weighting (0.6/0.4) is configurable but needs tuning with real embeddings
- When we switch to Bedrock embeddings in production, vector search quality will improve significantly, but hybrid will still outperform pure vector

## References

- [Reciprocal Rank Fusion paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Hybrid search in RAG systems](https://www.pinecone.io/learn/hybrid-search-intro/)
