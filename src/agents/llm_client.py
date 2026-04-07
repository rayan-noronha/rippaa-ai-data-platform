"""LLM client — abstracts Claude API calls for agents.

Supports two modes:
- 'anthropic': Direct Anthropic API (for development)
- 'bedrock': Claude via Amazon Bedrock (for production)
- 'mock': Returns placeholder responses (for testing without API key)

All agents use this client for LLM interactions.
"""

import json

import structlog

from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


def call_llm(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2000,
    temperature: float = 0.0,
) -> str:
    """Call the LLM and return the text response.

    Args:
        system_prompt: System instructions for the LLM.
        user_message: The user's message/query.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature (0.0 = deterministic).

    Returns:
        The LLM's text response.
    """
    settings = get_settings()

    if settings.anthropic_api_key:
        return _call_anthropic(system_prompt, user_message, max_tokens, temperature)
    elif settings.llm_provider == "bedrock" and settings.environment == "production":
        return _call_bedrock(system_prompt, user_message, max_tokens, temperature)
    else:
        return _call_mock(system_prompt, user_message)


def _call_anthropic(
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Claude via Anthropic API directly."""
    from anthropic import Anthropic

    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model=settings.llm_model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text
    logger.info(
        "LLM call complete (Anthropic)",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
    return text


def _call_bedrock(
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Call Claude via Amazon Bedrock."""
    import boto3

    settings = get_settings()
    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
    )

    response = client.invoke_model(
        modelId=settings.llm_model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    text = result["content"][0]["text"]
    logger.info(
        "LLM call complete (Bedrock)",
        input_tokens=result["usage"]["input_tokens"],
        output_tokens=result["usage"]["output_tokens"],
    )
    return text


def _call_mock(
    system_prompt: str,
    user_message: str,
) -> str:
    """Return a structured mock response for testing without an API key.

    Parses the system prompt to determine which agent is calling
    and returns an appropriate mock response.
    """
    logger.info("LLM call (mock mode — no API key configured)")

    if "query understanding" in system_prompt.lower():
        return json.dumps(
            {
                "intent": "information_retrieval",
                "rewritten_query": user_message,
                "search_strategy": "hybrid",
                "key_terms": user_message.split()[:5],
            }
        )

    elif "synthesise" in system_prompt.lower() or "synthesis" in system_prompt.lower():
        return (
            "Based on the retrieved documents, here is a summary of the relevant information. "
            "The documents contain details about enterprise policies, procedures, and guidelines "
            "that relate to your query. Please note that some information may be from documents "
            "of varying dates, and you should verify currency with the source documents."
        )

    elif "data quality" in system_prompt.lower():
        return json.dumps(
            {
                "quality_issues": [],
                "stale_documents": [],
                "conflicts": [],
                "overall_quality": "acceptable",
            }
        )

    else:
        return "Mock LLM response. Configure RIPPAA_ANTHROPIC_API_KEY in .env for real responses."
