"""Data Quality Agent — validates retrieved sources before synthesis.

Third agent in the RAG pipeline. Checks retrieved chunks for:
1. Source freshness (flags stale documents)
2. Conflicting information across sources
3. PII that may have been missed
4. Source diversity (not all from one document)
"""

import json
from datetime import UTC, datetime

import structlog
from sqlalchemy import text

from src.agents.llm_client import call_llm
from src.shared.database import get_engine

logger = structlog.get_logger(__name__)

QUALITY_SYSTEM_PROMPT = """You are a Data Quality agent for an enterprise document search system.
Your job is to review retrieved document chunks and flag any quality issues
before they are used to generate answers.

Given a list of retrieved chunks with their metadata, respond with ONLY a JSON object:
{
    "quality_issues": ["list of specific issues found"],
    "stale_documents": ["filenames of documents that appear outdated"],
    "conflicts": ["descriptions of any contradictory information between chunks"],
    "overall_quality": "one of: good, acceptable, poor",
    "recommendation": "brief recommendation for the synthesis agent"
}

Check for:
- Stale information: documents from before 2023 may be outdated
- Contradictions: two chunks stating different values for the same thing
- Over-reliance: all chunks from the same document = low diversity
- Missing context: chunks that seem incomplete or truncated
- PII remnants: any personal information that should have been masked"""


def check_quality(
    query: str,
    retrieved_chunks: list[dict],
) -> dict:
    """Validate the quality of retrieved chunks.

    Args:
        query: The user's original query.
        retrieved_chunks: List of chunks from the retrieval agent.

    Returns:
        Quality assessment with issues, warnings, and recommendations.
    """
    logger.info("Data quality check started", chunks_count=len(retrieved_chunks))

    if not retrieved_chunks:
        return {
            "quality_issues": ["No chunks retrieved — cannot answer query"],
            "stale_documents": [],
            "conflicts": [],
            "overall_quality": "poor",
            "recommendation": "Inform user that no relevant documents were found.",
        }

    # Check source diversity
    unique_documents = set(c.get("document_id") for c in retrieved_chunks)
    diversity_issue = None
    if len(unique_documents) == 1 and len(retrieved_chunks) > 1:
        diversity_issue = "All retrieved chunks come from a single document — answer may lack breadth"

    # Check for stale documents
    stale_docs = _check_staleness(retrieved_chunks)

    # Check for conflicting information using LLM
    chunks_summary = _format_chunks_for_quality_check(retrieved_chunks)
    llm_response = call_llm(
        system_prompt=QUALITY_SYSTEM_PROMPT,
        user_message=f"Query: {query}\n\nRetrieved chunks:\n{chunks_summary}",
        max_tokens=500,
        temperature=0.0,
    )

    try:
        quality_result = json.loads(llm_response.strip())
    except json.JSONDecodeError:
        quality_result = {
            "quality_issues": [],
            "stale_documents": [],
            "conflicts": [],
            "overall_quality": "acceptable",
            "recommendation": "Proceed with synthesis.",
        }

    # Merge our checks with LLM assessment
    if diversity_issue:
        quality_result.setdefault("quality_issues", []).append(diversity_issue)

    if stale_docs:
        quality_result.setdefault("stale_documents", []).extend(stale_docs)

    # Ensure all fields exist
    quality_result.setdefault("quality_issues", [])
    quality_result.setdefault("stale_documents", [])
    quality_result.setdefault("conflicts", [])
    quality_result.setdefault("overall_quality", "acceptable")
    quality_result.setdefault("recommendation", "Proceed with synthesis.")

    logger.info(
        "Data quality check complete",
        overall=quality_result["overall_quality"],
        issues=len(quality_result["quality_issues"]),
        conflicts=len(quality_result["conflicts"]),
    )

    return quality_result


def _check_staleness(chunks: list[dict]) -> list[str]:
    """Check if any retrieved chunks come from stale documents."""
    engine = get_engine()
    stale = []

    document_ids = list(set(c.get("document_id") for c in chunks if c.get("document_id")))
    if not document_ids:
        return []

    with engine.connect() as conn:
        for doc_id in document_ids:
            result = conn.execute(
                text("SELECT filename, ingested_at FROM documents WHERE id = :id"),
                {"id": doc_id},
            )
            row = result.fetchone()
            if row and row.ingested_at:
                age_days = (datetime.now(UTC) - row.ingested_at).days
                if age_days > 365:
                    stale.append(f"{row.filename} (ingested {age_days} days ago)")

    return stale


def _format_chunks_for_quality_check(chunks: list[dict]) -> str:
    """Format chunks into a readable summary for the LLM."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Chunk {i}] Source: {chunk.get('filename', 'unknown')} "
            f"(domain: {chunk.get('source_domain', 'unknown')})\n"
            f"{chunk.get('chunk_text', '')[:500]}"
        )
    return "\n\n".join(parts)
