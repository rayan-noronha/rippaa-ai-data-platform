# ADR-003: Use PySpark over pandas for Document Processing

## Status

Accepted

## Date

2026-03-25

## Context

We need a framework to process documents through the pipeline: parsing, chunking, PII detection, and embedding generation. The primary options considered were:

1. **pandas** — Single-machine, in-memory DataFrame library
2. **PySpark** — Distributed processing framework (can run locally in single-node mode)
3. **Polars** — Modern single-machine DataFrame library (Rust-based, faster than pandas)
4. **Dask** — Parallel computing library that scales pandas workflows

Key requirements:
- Process 50–1000+ documents in batch
- Handle documents of varying size (1KB text files to multi-MB PDFs)
- Scale beyond a single machine when needed
- Align with target employer tech stacks

## Decision

We will use **PySpark**, running locally in single-node mode for development and on AWS Glue/EMR Serverless for production.

## Rationale

### Scalability
- pandas loads everything into memory on a single machine — works for 50 documents, breaks at 10,000+
- PySpark distributes processing across a cluster, handling arbitrarily large document corpora
- Even in single-node mode, PySpark processes data in partitions, avoiding out-of-memory issues on large files

### Production deployment
- AWS Glue and EMR Serverless run PySpark jobs natively — no cluster management needed
- Glue auto-scales workers based on data volume — we pay only for what we use
- pandas would require a custom compute solution (Lambda, ECS) with manual memory management

### Employer alignment
- Spark appears in SEEK's and Easygo's job descriptions as a core requirement
- pandas does not appear in any $200k+ role we're targeting
- Demonstrating PySpark expertise signals ability to work at enterprise scale

### Trade-offs accepted
- PySpark has more boilerplate than pandas for simple transformations
- Local development requires Java runtime (bundled with PySpark)
- Learning curve is steeper for engineers familiar only with pandas
- For our current corpus size (53 documents), pandas would be faster to develop with

## Consequences

- All document processing jobs are written as PySpark scripts in `src/processing/spark_jobs/`
- Local development runs PySpark in single-node mode (no cluster needed)
- Production deployment targets AWS Glue or EMR Serverless
- We accept the development overhead of PySpark's API in exchange for production scalability and employer signal

## References

- [AWS Glue PySpark documentation](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-python.html)
- [EMR Serverless](https://aws.amazon.com/emr/serverless/)
