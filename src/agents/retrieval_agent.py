"""Retrieval Agent — finds relevant document chunks.

Second agent in the RAG pipeline. Uses the query understanding
output to execute the optimal search strategy and return
ranked, relevant chunks from pgvector.
"""

import structlog

from src.agents.tools.search import hybrid_search, keyword_search, vector_search

logger = structlog.get_logger(__name__)


def retrieve_chunks(
    query: str,
    rewritten_query: str,
    search_strategy: str = "hybrid",
    source_domains: list[str] | None = None,
    max_results: int = 5,
) -> list[dict]:
    """Retrieve relevant chunks based on the search strategy.

    Args:
        query: Original user query.
        rewritten_query: Optimised query from the query understanding agent.
        search_strategy: One of 'hybrid', 'vector', 'keyword'.
        source_domains: Optional domain filter.
        max_results: Maximum chunks to return.

    Returns:
        List of ranked chunk results with relevance scores.
    """
    logger.info(
        "Retrieval started",
        strategy=search_strategy,
        query=rewritten_query[:100],
        domains=source_domains,
    )

    # Use rewritten query for search
    search_query = rewritten_query or query

    # Convert empty list to None for search functions
    domains = source_domains if source_domains else None

    if search_strategy == "vector":
        results = vector_search(search_query, limit=max_results, source_domains=domains)
    elif search_strategy == "keyword":
        results = keyword_search(search_query, limit=max_results, source_domains=domains)
    else:
        # Default: hybrid search
        results = hybrid_search(search_query, limit=max_results, source_domains=domains)

    logger.info(
        "Retrieval complete",
        strategy=search_strategy,
        results_count=len(results),
        top_score=results[0]["relevance_score"] if results else 0,
    )

    return results
