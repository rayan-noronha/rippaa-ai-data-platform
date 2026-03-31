"""Agent Orchestrator — coordinates the agentic RAG pipeline.

Runs the four agents in sequence:
1. Query Understanding → classifies intent, rewrites query
2. Retrieval → hybrid search for relevant chunks
3. Data Quality → validates sources before synthesis
4. Synthesis → generates cited answer

Also handles logging, timing, and error recovery.
"""

import time
from uuid import uuid4

import structlog
from sqlalchemy import text

from src.shared.database import get_engine
from src.agents.query_agent import understand_query
from src.agents.retrieval_agent import retrieve_chunks
from src.agents.quality_agent import check_quality
from src.agents.synthesis_agent import synthesise_answer

logger = structlog.get_logger(__name__)


def run_query(
    query: str,
    max_results: int = 5,
    source_domains: list[str] | None = None,
) -> dict:
    """Execute the full agentic RAG pipeline.

    Args:
        query: The user's natural language question.
        max_results: Maximum chunks to retrieve.
        source_domains: Optional domain filter.

    Returns:
        Complete response with answer, sources, metadata, and timing.
    """
    start_time = time.time()
    query_id = str(uuid4())

    logger.info("RAG pipeline started", query_id=query_id, query=query[:100])

    try:
        # ── Agent 1: Query Understanding ──────────
        t1 = time.time()
        query_understanding = understand_query(query)
        t1_elapsed = time.time() - t1

        # Use agent's recommended strategy and domains
        search_strategy = query_understanding.get("search_strategy", "hybrid")
        rewritten_query = query_understanding.get("rewritten_query", query)
        agent_domains = query_understanding.get("source_domains", [])

        # User-specified domains override agent recommendation
        effective_domains = source_domains if source_domains else (agent_domains or None)

        # ── Agent 2: Retrieval ────────────────────
        t2 = time.time()
        retrieved_chunks = retrieve_chunks(
            query=query,
            rewritten_query=rewritten_query,
            search_strategy=search_strategy,
            source_domains=effective_domains,
            max_results=max_results,
        )
        t2_elapsed = time.time() - t2

        # ── Agent 3: Data Quality ─────────────────
        t3 = time.time()
        quality_assessment = check_quality(query, retrieved_chunks)
        t3_elapsed = time.time() - t3

        # ── Agent 4: Synthesis ────────────────────
        t4 = time.time()
        synthesis_result = synthesise_answer(
            query=query,
            retrieved_chunks=retrieved_chunks,
            quality_assessment=quality_assessment,
            query_understanding=query_understanding,
        )
        t4_elapsed = time.time() - t4

        total_elapsed = time.time() - start_time

        # Build response
        response = {
            "query_id": query_id,
            "query": query,
            "answer": synthesis_result["answer"],
            "sources": synthesis_result["sources"],
            "metadata": {
                "intent": query_understanding.get("intent"),
                "rewritten_query": rewritten_query,
                "search_strategy": search_strategy,
                "chunks_retrieved": len(retrieved_chunks),
                "quality": quality_assessment.get("overall_quality"),
                "quality_issues": quality_assessment.get("quality_issues", []),
                "conflicts": quality_assessment.get("conflicts", []),
            },
            "timing": {
                "query_understanding_ms": round(t1_elapsed * 1000),
                "retrieval_ms": round(t2_elapsed * 1000),
                "quality_check_ms": round(t3_elapsed * 1000),
                "synthesis_ms": round(t4_elapsed * 1000),
                "total_ms": round(total_elapsed * 1000),
            },
        }

        # Log to query_log table
        _log_query(query_id, query, rewritten_query, query_understanding, retrieved_chunks, synthesis_result, total_elapsed)

        logger.info(
            "RAG pipeline complete",
            query_id=query_id,
            total_ms=response["timing"]["total_ms"],
            chunks=len(retrieved_chunks),
            quality=quality_assessment.get("overall_quality"),
        )

        return response

    except Exception as e:
        total_elapsed = time.time() - start_time
        logger.exception("RAG pipeline failed", query_id=query_id, error=str(e))
        return {
            "query_id": query_id,
            "query": query,
            "answer": f"An error occurred while processing your query: {str(e)}",
            "sources": [],
            "metadata": {"error": str(e)},
            "timing": {"total_ms": round(total_elapsed * 1000)},
        }


def _log_query(
    query_id: str,
    query: str,
    rewritten_query: str,
    understanding: dict,
    chunks: list[dict],
    synthesis: dict,
    elapsed: float,
) -> None:
    """Log the query and response to the audit table."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO query_log (id, query_text, rewritten_query, intent,
                                          retrieval_strategy, chunks_retrieved, response_text, latency_ms)
                    VALUES (:id, :query, :rewritten, :intent, :strategy, :chunks, :response, :latency)
                """),
                {
                    "id": query_id,
                    "query": query,
                    "rewritten": rewritten_query,
                    "intent": understanding.get("intent"),
                    "strategy": understanding.get("search_strategy"),
                    "chunks": len(chunks),
                    "response": synthesis.get("answer", "")[:5000],
                    "latency": round(elapsed * 1000),
                },
            )
            conn.commit()
    except Exception:
        logger.exception("Failed to log query")
