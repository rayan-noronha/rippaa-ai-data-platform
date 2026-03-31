"""Search tools for the retrieval agent.

Provides two search strategies:
- Vector search: cosine similarity against pgvector embeddings
- Keyword search: PostgreSQL full-text search with ts_rank

Both return ranked results that the retrieval agent combines
for hybrid search.
"""

import json

import structlog
from sqlalchemy import text

from src.shared.database import get_engine
from src.processing.embedder import generate_embedding

logger = structlog.get_logger(__name__)


def vector_search(
    query: str,
    limit: int = 10,
    source_domains: list[str] | None = None,
) -> list[dict]:
    """Search chunks by embedding cosine similarity.

    Args:
        query: The search query text.
        limit: Maximum number of results.
        source_domains: Optional filter by domain.

    Returns:
        List of matching chunks with relevance scores.
    """
    # Generate embedding for the query
    query_embedding = generate_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    engine = get_engine()

    # Build query with optional domain filter
    domain_filter = ""
    params: dict = {"embedding": embedding_str, "limit": limit}

    if source_domains:
        domain_filter = "AND d.source_domain = ANY(:domains)"
        params["domains"] = source_domains

    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                SELECT
                    c.id AS chunk_id,
                    c.document_id,
                    c.chunk_text,
                    c.chunk_index,
                    c.token_count,
                    c.metadata,
                    d.filename,
                    d.source_domain,
                    1 - (c.embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.embedding IS NOT NULL
                {domain_filter}
                ORDER BY c.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """),
            params,
        )

        results = [
            {
                "chunk_id": str(row.chunk_id),
                "document_id": str(row.document_id),
                "chunk_text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "token_count": row.token_count,
                "filename": row.filename,
                "source_domain": row.source_domain,
                "relevance_score": round(float(row.similarity), 4),
                "search_type": "vector",
            }
            for row in result
        ]

    logger.info("Vector search complete", query_length=len(query), results=len(results))
    return results


def keyword_search(
    query: str,
    limit: int = 10,
    source_domains: list[str] | None = None,
) -> list[dict]:
    """Search chunks using PostgreSQL full-text search.

    Args:
        query: The search query text.
        limit: Maximum number of results.
        source_domains: Optional filter by domain.

    Returns:
        List of matching chunks with relevance scores.
    """
    engine = get_engine()

    # Build domain filter
    domain_filter = ""
    params: dict = {"query": query, "limit": limit}

    if source_domains:
        domain_filter = "AND d.source_domain = ANY(:domains)"
        params["domains"] = source_domains

    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                SELECT
                    c.id AS chunk_id,
                    c.document_id,
                    c.chunk_text,
                    c.chunk_index,
                    c.token_count,
                    c.metadata,
                    d.filename,
                    d.source_domain,
                    ts_rank(
                        to_tsvector('english', c.chunk_text),
                        plainto_tsquery('english', :query)
                    ) AS rank
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE to_tsvector('english', c.chunk_text) @@ plainto_tsquery('english', :query)
                {domain_filter}
                ORDER BY rank DESC
                LIMIT :limit
            """),
            params,
        )

        results = [
            {
                "chunk_id": str(row.chunk_id),
                "document_id": str(row.document_id),
                "chunk_text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "token_count": row.token_count,
                "filename": row.filename,
                "source_domain": row.source_domain,
                "relevance_score": round(float(row.rank), 4),
                "search_type": "keyword",
            }
            for row in result
        ]

    logger.info("Keyword search complete", query=query[:50], results=len(results))
    return results


def hybrid_search(
    query: str,
    limit: int = 5,
    source_domains: list[str] | None = None,
    vector_weight: float = 0.6,
    keyword_weight: float = 0.4,
) -> list[dict]:
    """Combine vector and keyword search with weighted scoring.

    Reciprocal Rank Fusion (RRF) is used to merge results:
    score = vector_weight * (1 / vector_rank) + keyword_weight * (1 / keyword_rank)

    Args:
        query: The search query text.
        limit: Maximum number of final results.
        source_domains: Optional filter by domain.
        vector_weight: Weight for vector search results (0-1).
        keyword_weight: Weight for keyword search results (0-1).

    Returns:
        Merged, de-duplicated, re-ranked results.
    """
    # Get results from both strategies
    vector_results = vector_search(query, limit=limit * 2, source_domains=source_domains)
    keyword_results = keyword_search(query, limit=limit * 2, source_domains=source_domains)

    # Build score map using Reciprocal Rank Fusion
    scores: dict[str, dict] = {}

    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result["chunk_id"]
        rrf_score = vector_weight * (1.0 / (rank + 60))  # RRF constant = 60
        if chunk_id not in scores:
            scores[chunk_id] = {**result, "rrf_score": 0.0, "search_types": []}
        scores[chunk_id]["rrf_score"] += rrf_score
        scores[chunk_id]["search_types"].append("vector")

    for rank, result in enumerate(keyword_results, start=1):
        chunk_id = result["chunk_id"]
        rrf_score = keyword_weight * (1.0 / (rank + 60))
        if chunk_id not in scores:
            scores[chunk_id] = {**result, "rrf_score": 0.0, "search_types": []}
        scores[chunk_id]["rrf_score"] += rrf_score
        if "keyword" not in scores[chunk_id].get("search_types", []):
            scores[chunk_id]["search_types"].append("keyword")

    # Sort by RRF score and return top results
    ranked = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)[:limit]

    # Normalize scores to 0-1 range
    if ranked:
        max_score = ranked[0]["rrf_score"]
        for result in ranked:
            result["relevance_score"] = round(result["rrf_score"] / max_score, 4) if max_score > 0 else 0.0
            result["search_type"] = "+".join(result["search_types"])
            del result["rrf_score"]
            del result["search_types"]

    logger.info(
        "Hybrid search complete",
        query=query[:50],
        vector_results=len(vector_results),
        keyword_results=len(keyword_results),
        final_results=len(ranked),
    )

    return ranked
