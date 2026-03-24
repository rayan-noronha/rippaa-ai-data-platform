"""Synthetic data generator for the RIPPAA AI Data Platform.

Generates realistic enterprise documents across 4 domains:
- Insurance: policy wordings, claims reports, underwriting guidelines
- Financial: regulatory filings, compliance docs, risk assessments
- Government: council policies, procurement guidelines, internal memos
- Enterprise: HR policies, IT security docs, vendor contracts

Intentionally includes data quality issues to test pipeline robustness:
- PII leakage (names, emails, ABNs, Medicare numbers)
- Missing fields and inconsistent formats
- Duplicate documents with variant metadata
- Stale/outdated documents
- Conflicting information across documents
- Malformed files (corrupted PDF, misaligned CSV)

Usage:
    python scripts/seed_data.py [--output-dir data/synthetic] [--count 50]
"""

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> None:
    """Generate synthetic documents and save to output directory."""
    parser = argparse.ArgumentParser(description="Generate synthetic test documents")
    parser.add_argument("--output-dir", type=str, default="data/synthetic", help="Output directory")
    parser.add_argument("--count", type=int, default=50, help="Number of documents to generate")
    args = parser.parse_args()

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # TODO: Implement document generation using Claude API + Faker
    # Phase 1 will build this out with realistic multi-domain documents
    print(f"🚧 Synthetic data generation coming in Phase 1")
    print(f"   Output directory: {output_path}")
    print(f"   Target count: {args.count} documents")


if __name__ == "__main__":
    main()
