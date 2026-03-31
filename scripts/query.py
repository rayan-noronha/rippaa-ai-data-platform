"""Query the RIPPAA AI Data Platform knowledge base.

Runs the full agentic RAG pipeline:
Query Understanding → Retrieval → Data Quality → Synthesis

Usage:
    python -m scripts.query "What is the claims process?"
    python -m scripts.query "What are the compliance requirements?" --domain financial
    python -m scripts.query "What is the maximum coverage for residential property?" --domain insurance
"""

import argparse
import json
import sys


def main() -> None:
    """Run an interactive query session or a single query."""
    parser = argparse.ArgumentParser(description="Query the RIPPAA knowledge base")
    parser.add_argument("query", nargs="?", help="Query to run (omit for interactive mode)")
    parser.add_argument("--domain", type=str, help="Filter by domain (insurance, financial, government, enterprise)")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum chunks to retrieve")
    args = parser.parse_args()

    from src.agents.orchestrator import run_query

    if args.query:
        # Single query mode
        _run_single_query(args.query, args.domain, args.max_results)
    else:
        # Interactive mode
        _run_interactive(args.domain, args.max_results)


def _run_single_query(query: str, domain: str | None, max_results: int) -> None:
    """Run a single query and display results."""
    from src.agents.orchestrator import run_query

    print("🔍 RIPPAA AI Data Platform — Knowledge Base Query")
    print(f"   Query: {query}")
    if domain:
        print(f"   Domain: {domain}")
    print()

    domains = [domain] if domain else None
    result = run_query(query, max_results=max_results, source_domains=domains)

    _display_result(result)


def _run_interactive(domain: str | None, max_results: int) -> None:
    """Run an interactive query session."""
    from src.agents.orchestrator import run_query

    print("🔍 RIPPAA AI Data Platform — Interactive Query Mode")
    print("   Type your questions. Type 'quit' to exit.")
    print()

    while True:
        try:
            query = input("❓ Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not query or query.lower() in ("quit", "exit", "q"):
            print("👋 Goodbye!")
            break

        domains = [domain] if domain else None
        result = run_query(query, max_results=max_results, source_domains=domains)
        _display_result(result)
        print()


def _display_result(result: dict) -> None:
    """Pretty-print a query result."""
    print("=" * 70)
    print("📝 ANSWER:")
    print("=" * 70)
    print(result.get("answer", "No answer available."))
    print()

    # Sources
    sources = result.get("sources", [])
    if sources:
        print("📚 SOURCES:")
        for i, src in enumerate(sources, 1):
            print(f"   {i}. {src['filename']} ({src['source_domain']}) — relevance: {src.get('relevance_score', 'N/A')}")
        print()

    # Metadata
    metadata = result.get("metadata", {})
    timing = result.get("timing", {})

    print("📊 METADATA:")
    print(f"   Intent: {metadata.get('intent', 'N/A')}")
    print(f"   Rewritten query: {metadata.get('rewritten_query', 'N/A')}")
    print(f"   Search strategy: {metadata.get('search_strategy', 'N/A')}")
    print(f"   Chunks retrieved: {metadata.get('chunks_retrieved', 0)}")
    print(f"   Quality: {metadata.get('quality', 'N/A')}")

    issues = metadata.get("quality_issues", [])
    if issues:
        print(f"   ⚠️  Issues: {', '.join(issues)}")

    conflicts = metadata.get("conflicts", [])
    if conflicts:
        print(f"   ⚠️  Conflicts: {', '.join(conflicts)}")

    print()
    print("⏱️  TIMING:")
    print(f"   Query understanding: {timing.get('query_understanding_ms', 'N/A')}ms")
    print(f"   Retrieval: {timing.get('retrieval_ms', 'N/A')}ms")
    print(f"   Quality check: {timing.get('quality_check_ms', 'N/A')}ms")
    print(f"   Synthesis: {timing.get('synthesis_ms', 'N/A')}ms")
    print(f"   Total: {timing.get('total_ms', 'N/A')}ms")
    print("=" * 70)


if __name__ == "__main__":
    main()
