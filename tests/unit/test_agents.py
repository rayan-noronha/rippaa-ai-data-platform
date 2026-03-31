"""Tests for the agentic RAG system."""

from src.agents.query_agent import understand_query
from src.agents.synthesis_agent import synthesise_answer


class TestQueryAgent:
    """Test query understanding agent."""

    def test_understand_basic_query(self) -> None:
        """Should classify a basic information retrieval query."""
        result = understand_query("What is the claims process?")
        assert "intent" in result
        assert "rewritten_query" in result
        assert "search_strategy" in result
        assert "source_domains" in result
        assert result["intent"] in ("information_retrieval", "factual", "comparison", "procedural")

    def test_understand_returns_strategy(self) -> None:
        """Should return a valid search strategy."""
        result = understand_query("Compare home and motor insurance coverage")
        assert result["search_strategy"] in ("hybrid", "vector", "keyword")

    def test_understand_preserves_query(self) -> None:
        """Rewritten query should not be empty."""
        result = understand_query("How do I lodge a claim?")
        assert len(result["rewritten_query"]) > 0

    def test_understand_returns_domains_list(self) -> None:
        """Source domains should be a list."""
        result = understand_query("What are the APRA compliance requirements?")
        assert isinstance(result["source_domains"], list)


class TestSynthesisAgent:
    """Test synthesis agent."""

    def test_synthesise_with_chunks(self) -> None:
        """Should generate an answer from chunks."""
        chunks = [
            {
                "chunk_text": "The claims process involves contacting the claims team within 30 days.",
                "filename": "policy_001.txt",
                "source_domain": "insurance",
                "document_id": "test-doc-1",
                "relevance_score": 0.95,
            },
            {
                "chunk_text": "A claims assessor will be assigned within 2 business days.",
                "filename": "policy_002.txt",
                "source_domain": "insurance",
                "document_id": "test-doc-2",
                "relevance_score": 0.90,
            },
        ]
        quality = {"overall_quality": "good", "quality_issues": [], "conflicts": [], "recommendation": "Proceed"}
        understanding = {"intent": "information_retrieval"}

        result = synthesise_answer(
            query="What is the claims process?",
            retrieved_chunks=chunks,
            quality_assessment=quality,
            query_understanding=understanding,
        )

        assert "answer" in result
        assert "sources" in result
        assert len(result["answer"]) > 0
        assert len(result["sources"]) == 2

    def test_synthesise_empty_chunks(self) -> None:
        """Should handle empty chunks gracefully."""
        quality = {"overall_quality": "poor", "quality_issues": ["No relevant sources found"], "conflicts": [], "recommendation": "Proceed"}
        understanding = {"intent": "information_retrieval"}

        result = synthesise_answer(
            query="Something irrelevant",
            retrieved_chunks=[],
            quality_assessment=quality,
            query_understanding=understanding,
        )

        assert "answer" in result
        assert len(result["answer"]) > 0

    def test_synthesise_includes_sources(self) -> None:
        """Sources should include filename and domain."""
        chunks = [
            {
                "chunk_text": "Test content about insurance.",
                "filename": "test_doc.txt",
                "source_domain": "insurance",
                "document_id": "doc-123",
                "relevance_score": 0.85,
            },
        ]
        quality = {"overall_quality": "acceptable", "quality_issues": [], "conflicts": [], "recommendation": "Proceed"}
        understanding = {"intent": "information_retrieval"}

        result = synthesise_answer(
            query="Tell me about insurance",
            retrieved_chunks=chunks,
            quality_assessment=quality,
            query_understanding=understanding,
        )

        assert len(result["sources"]) == 1
        assert result["sources"][0]["filename"] == "test_doc.txt"
        assert result["sources"][0]["source_domain"] == "insurance"
