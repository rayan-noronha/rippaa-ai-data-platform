# ADR-009: Chunking Strategy Selection

## Status

Accepted

## Date

2026-03-31

## Context

Documents must be split into chunks before embedding. The chunk size directly impacts retrieval quality, embedding cost, and answer accuracy. Key trade-offs:

- **Too large** (>1000 tokens): Diluted semantic meaning, less precise retrieval, higher embedding cost
- **Too small** (<100 tokens): Lost context, fragmented information, more chunks to search
- **No overlap**: Context lost at chunk boundaries — a sentence split across two chunks is unsearchable
- **Too much overlap**: Redundant embeddings, wasted storage and compute

Options considered:

1. **Fixed-size with overlap** — Split at ~500 tokens with 50 token overlap, break at sentence boundaries
2. **Semantic chunking** — Use an LLM or NLP model to identify topic boundaries
3. **Recursive/hierarchical** — Split by section headers, then paragraphs, then sentences
4. **Sliding window** — Fixed window with configurable step size

## Decision

We use **fixed-size chunking at 500 tokens with 50 token overlap**, breaking at sentence boundaries when possible.

## Rationale

### Why 500 tokens
- Matches the sweet spot for embedding models (Titan Embed v2 handles up to 8192 tokens but quality degrades for long inputs)
- Provides enough context for a coherent passage while being specific enough for precise retrieval
- At 128 chunks for 53 documents, our average document produces 2-3 chunks — manageable for search

### Why 50 token overlap
- Prevents information loss at chunk boundaries
- A sentence that spans two chunks appears in both, ensuring it's retrievable
- 10% overlap is industry standard — enough for continuity without excessive redundancy

### Why sentence boundary breaking
- Chunks that end mid-sentence produce poor embeddings
- Our break-point algorithm searches backwards from the target split position for sentence endings (. ! ?), then paragraph breaks, then word boundaries
- This produces more natural, readable chunks

### Why not semantic chunking
- Requires an additional LLM call per document — adds cost and latency
- Fixed-size with sentence-boundary breaking achieves 80% of the benefit at 0% of the cost
- Can be added as an enhancement later if retrieval quality needs improvement

## Consequences

- All documents are chunked consistently regardless of format
- Chunk sizes vary slightly (450-550 tokens) due to sentence-boundary breaking
- The overlap means ~10% storage overhead
- Chunking strategy is configurable — can be changed per document type in future

## References

- [Chunking strategies for RAG](https://www.pinecone.io/learn/chunking-strategies/)
- [LlamaIndex chunking guide](https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/)
