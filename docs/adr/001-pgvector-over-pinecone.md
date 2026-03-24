# ADR-001: Use pgvector over Pinecone for Vector Storage

## Status

Accepted

## Date

2026-03-24

## Context

We need a vector database to store document embeddings for semantic search and RAG retrieval. The primary options considered were:

1. **Pinecone** — Fully managed vector database, purpose-built for similarity search
2. **pgvector** — PostgreSQL extension that adds vector similarity search to standard PostgreSQL
3. **Weaviate** — Open-source vector database with built-in vectorisation
4. **Qdrant** — Open-source vector database with advanced filtering

Key requirements:
- Store ~100k–1M embedding vectors (1024 dimensions)
- Support hybrid search (vector similarity + metadata filtering)
- Minimise infrastructure complexity
- Keep costs low during development and early production
- Avoid vendor lock-in
- Demonstrate SQL depth (relevant for target employer job descriptions)

## Decision

We will use **pgvector** (PostgreSQL extension) on Amazon RDS.

## Rationale

### Cost
- pgvector on RDS db.t3.micro: ~$15/month
- Pinecone Starter: free but limited; Standard: ~$70/month for equivalent usage
- At our scale (dev + demo), pgvector is 4–5x cheaper

### Infrastructure simplicity
- We already need PostgreSQL for the document registry, metadata store, and query audit log
- pgvector adds vector capability to the same database — one service to manage instead of two
- Fewer moving parts = fewer failure modes = more reliable demos

### No vendor lock-in
- pgvector runs on standard PostgreSQL — can run on any cloud, on-prem, or locally in Docker
- Pinecone is proprietary — switching costs are high once embedded in the pipeline

### Skill signal
- Every job description we're targeting lists SQL as a core requirement
- Using PostgreSQL for vector storage demonstrates that we can solve problems with existing tools rather than adding unnecessary infrastructure
- Shows cost-conscious thinking — a principal engineer's job is to reduce complexity, not add it

### Trade-offs accepted
- Pinecone has better query performance at very large scale (10M+ vectors) — our corpus doesn't require this
- Pinecone offers managed scaling, replication, and backups out of the box — we accept the operational overhead of managing RDS
- pgvector's HNSW/IVFFlat indexes require tuning — we document our index configuration choices

## Consequences

- We manage pgvector extension upgrades and index tuning ourselves
- We need to monitor query latency and optimise indexes as the corpus grows
- If the project scales beyond ~5M vectors, we should re-evaluate this decision
- We gain a single PostgreSQL instance that handles metadata, vectors, and audit logs — simplifying deployment, backup, and monitoring

## References

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Pinecone Pricing](https://www.pinecone.io/pricing/)
- [pgvector vs Pinecone benchmark](https://supabase.com/blog/pgvector-vs-pinecone)
