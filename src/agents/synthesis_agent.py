"""Synthesis Agent — generates answers with source citations.

Final agent in the RAG pipeline. Takes the retrieved chunks,
quality assessment, and original query, then generates a
comprehensive answer with inline source citations.
"""

import structlog

from src.agents.llm_client import call_llm

logger = structlog.get_logger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are a Synthesis agent for an enterprise document search system.
Your job is to generate accurate, well-cited answers based on retrieved document chunks.

RULES:
1. ONLY use information from the provided chunks — never make up information
2. Cite sources inline using [Source: filename] format
3. If chunks contain conflicting information, acknowledge both versions
4. If the quality assessment flags issues, mention relevant caveats
5. If no chunks are relevant to the query, say so honestly
6. Be concise but thorough — aim for 2-4 paragraphs
7. Use professional, clear language suitable for enterprise users
8. If PII-masked tokens appear (like [EMAIL_REDACTED]), leave them as-is

RESPONSE FORMAT:
Provide a clear, direct answer to the query with inline citations.
End with a "Sources" section listing all referenced documents."""


def synthesise_answer(
    query: str,
    retrieved_chunks: list[dict],
    quality_assessment: dict,
    query_understanding: dict,
) -> dict:
    """Generate a cited answer from retrieved chunks.

    Args:
        query: The user's original query.
        retrieved_chunks: Ranked chunks from the retrieval agent.
        quality_assessment: Quality check results from the data quality agent.
        query_understanding: Intent and context from the query understanding agent.

    Returns:
        Dictionary with answer text, sources, and metadata.
    """
    logger.info("Synthesis started", query=query[:100], chunks=len(retrieved_chunks))

    if not retrieved_chunks:
        return {
            "answer": "I couldn't find any relevant documents to answer your query. "
                      "Please try rephrasing your question or broadening the search scope.",
            "sources": [],
            "quality_notes": quality_assessment.get("quality_issues", []),
        }

    # Build context for the LLM
    context = _build_context(retrieved_chunks, quality_assessment)

    user_message = f"""Query: {query}
Intent: {query_understanding.get('intent', 'unknown')}

Quality Assessment:
- Overall quality: {quality_assessment.get('overall_quality', 'unknown')}
- Issues: {', '.join(quality_assessment.get('quality_issues', [])) or 'None'}
- Conflicts: {', '.join(quality_assessment.get('conflicts', [])) or 'None'}
- Recommendation: {quality_assessment.get('recommendation', 'Proceed')}

Retrieved Documents:
{context}

Please synthesise a comprehensive, cited answer to the query."""

    answer_text = call_llm(
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        user_message=user_message,
        max_tokens=2000,
        temperature=0.0,
    )

    # Extract unique sources
    sources = _extract_sources(retrieved_chunks)

    result = {
        "answer": answer_text,
        "sources": sources,
        "quality_notes": quality_assessment.get("quality_issues", []),
        "intent": query_understanding.get("intent", "unknown"),
        "chunks_used": len(retrieved_chunks),
    }

    logger.info(
        "Synthesis complete",
        answer_length=len(answer_text),
        sources_count=len(sources),
    )

    return result


def _build_context(chunks: list[dict], quality: dict) -> str:
    """Build the context string from retrieved chunks."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        relevance = chunk.get("relevance_score", 0)
        parts.append(
            f"--- Document {i} ---\n"
            f"Filename: {chunk.get('filename', 'unknown')}\n"
            f"Domain: {chunk.get('source_domain', 'unknown')}\n"
            f"Relevance: {relevance}\n"
            f"Search type: {chunk.get('search_type', 'unknown')}\n"
            f"Content:\n{chunk.get('chunk_text', '')}\n"
        )
    return "\n".join(parts)


def _extract_sources(chunks: list[dict]) -> list[dict]:
    """Extract unique source documents from chunks."""
    seen = set()
    sources = []
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            sources.append({
                "document_id": doc_id,
                "filename": chunk.get("filename", "unknown"),
                "source_domain": chunk.get("source_domain", "unknown"),
                "relevance_score": chunk.get("relevance_score", 0),
            })
    return sources
