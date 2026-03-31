"""Query Understanding Agent — classifies intent and rewrites queries.

First agent in the RAG pipeline. Analyses the user's query to:
1. Classify the intent (factual lookup, comparison, procedural, analytical)
2. Rewrite the query for better retrieval
3. Extract key terms for keyword search
4. Select the optimal search strategy
"""

import json

import structlog

from src.agents.llm_client import call_llm

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a Query Understanding agent for an enterprise document search system.
Your job is to analyse user queries and prepare them for retrieval from a knowledge base
containing insurance policies, financial compliance reports, government council policies,
and enterprise HR/IT documents.

Given a user query, respond with ONLY a JSON object (no markdown, no explanation):
{
    "intent": "one of: factual_lookup, comparison, procedural, analytical, definition",
    "rewritten_query": "an improved version of the query optimised for document search",
    "search_strategy": "one of: hybrid, vector, keyword",
    "key_terms": ["list", "of", "important", "search", "terms"],
    "source_domains": ["list of relevant domains: insurance, financial, government, enterprise, or empty for all"]
}

Guidelines:
- factual_lookup: "What is the claims process?" "What is the maximum coverage?"
- comparison: "How do policy limits differ between residential and commercial?"
- procedural: "How do I submit a claim?" "What are the steps to..."
- analytical: "What risks were identified?" "Summarise the compliance findings"
- definition: "What is an ABN?" "Define excess"
- For rewritten_query: expand abbreviations, add context, make it specific
- For search_strategy: use 'keyword' for exact terms, 'vector' for semantic, 'hybrid' for most queries
- For source_domains: narrow to relevant domains when the query clearly targets one industry"""


def understand_query(query: str) -> dict:
    """Analyse a user query and prepare it for retrieval.

    Args:
        query: The raw user query.

    Returns:
        Dictionary with intent, rewritten_query, search_strategy,
        key_terms, and source_domains.
    """
    logger.info("Query understanding started", query=query[:100])

    response = call_llm(
        system_prompt=SYSTEM_PROMPT,
        user_message=query,
        max_tokens=500,
        temperature=0.0,
    )

    try:
        # Parse JSON response
        result = json.loads(response.strip())
    except json.JSONDecodeError:
        # If LLM returns non-JSON, use defaults
        logger.warning("Query understanding returned non-JSON, using defaults")
        result = {
            "intent": "factual_lookup",
            "rewritten_query": query,
            "search_strategy": "hybrid",
            "key_terms": query.split()[:5],
            "source_domains": [],
        }

    # Ensure all required fields exist
    result.setdefault("intent", "factual_lookup")
    result.setdefault("rewritten_query", query)
    result.setdefault("search_strategy", "hybrid")
    result.setdefault("key_terms", [])
    result.setdefault("source_domains", [])

    logger.info(
        "Query understood",
        intent=result["intent"],
        strategy=result["search_strategy"],
        domains=result["source_domains"],
    )

    return result
