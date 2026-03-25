# ADR-004: Use Claude via Amazon Bedrock over OpenAI for LLM

## Status

Accepted

## Date

2026-03-25

## Context

We need a Large Language Model (LLM) for two purposes:
1. **Embedding generation** — Converting document text into vector representations for semantic search
2. **Answer synthesis** — Generating answers from retrieved document chunks in the RAG pipeline

Options considered:

1. **Claude (Anthropic) via Amazon Bedrock** — Managed access to Claude models through AWS
2. **OpenAI GPT-4 via API** — Direct API access to OpenAI models
3. **Claude via Anthropic API** — Direct API access to Claude
4. **Open-source models (Llama, Mistral)** — Self-hosted on SageMaker or EC2

Key requirements:
- High-quality document analysis and reasoning
- Enterprise-grade security and compliance
- Cost-effective for development and production
- Integration with existing AWS infrastructure
- Vendor flexibility (ability to swap models)

## Decision

We will use **Claude via Amazon Bedrock** as the primary LLM, with **Amazon Titan** for embedding generation.

## Rationale

### Enterprise integration
- Bedrock integrates natively with AWS IAM — no separate API keys to manage
- All LLM calls go through AWS CloudTrail — full audit trail for regulated industries
- VPC endpoints available — LLM calls never leave the AWS network
- CBA, Suncorp, and other Australian enterprises are AWS-heavy — Bedrock is the path of least resistance for their procurement teams

### Vendor flexibility
- Bedrock provides a unified API for Claude, Llama, Mistral, Titan, and others
- Switching from Claude to another model requires changing one configuration value, not rewriting integration code
- This protects against vendor lock-in and price changes

### Model quality
- Claude excels at document analysis, long-context reasoning, and following complex instructions
- For RAG synthesis (generating answers with source citations), Claude's instruction-following capability is critical
- Claude handles the nuance of insurance policy language, regulatory compliance text, and technical documentation well

### Embedding strategy
- Amazon Titan Embed Text v2 for embeddings (1024 dimensions) — cost-effective and Bedrock-native
- Keeps all AI services within the Bedrock ecosystem — one billing relationship, one set of permissions

### Cost comparison (approximate, for development)
- Bedrock Claude Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output tokens
- OpenAI GPT-4o: ~$2.50 per 1M input tokens, ~$10 per 1M output tokens
- Bedrock Titan embeddings: ~$0.02 per 1M tokens
- OpenAI text-embedding-3-small: ~$0.02 per 1M tokens
- Costs are comparable; the enterprise integration benefits of Bedrock outweigh marginal price differences

### Trade-offs accepted
- Bedrock model availability can lag behind direct API releases (new Claude versions appear on Bedrock days/weeks later)
- OpenAI has a larger ecosystem of tools and libraries
- For local development without AWS credentials, we fall back to the Anthropic API directly (configurable via environment variable)

## Consequences

- LLM provider is configurable: `RIPPAA_LLM_PROVIDER=bedrock` (production) or `RIPPAA_LLM_PROVIDER=anthropic` (local dev)
- All LLM interactions go through an abstraction layer — swapping providers requires no changes to business logic
- Embedding model is Amazon Titan (1024 dimensions) — this determines our pgvector column size
- We budget ~$10–20/month for Bedrock API calls during development

## References

- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [Claude on Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html)
- [Amazon Titan Embeddings](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
