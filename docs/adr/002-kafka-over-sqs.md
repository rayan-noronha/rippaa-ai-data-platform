# ADR-002: Use Kafka (MSK) over SQS for Event Streaming

## Status

Accepted

## Date

2026-03-24

## Context

We need an event streaming layer between the ingestion and processing components. Documents arrive in S3, trigger processing, and the results flow through multiple stages (parsing → chunking → PII detection → embedding → storage). Options considered:

1. **Amazon MSK (Managed Kafka)** — Fully managed Apache Kafka
2. **Amazon SQS** — Fully managed message queue
3. **Amazon Kinesis** — Managed streaming service
4. **Self-hosted Kafka** — Kafka on EC2/ECS

Key requirements:
- Decouple ingestion from processing
- Support message replay (reprocess failed documents without re-ingestion)
- Handle ordering within a document's processing stages
- Observable (monitor lag, throughput, consumer health)
- Align with target employer tech stacks

## Decision

We will use **Amazon MSK Serverless** (managed Kafka) in production and **Confluent Kafka Docker image** for local development.

## Rationale

### Message replay
- Kafka retains messages on the topic — we can replay and reprocess any document without re-ingestion
- SQS deletes messages after consumption — no replay without a separate archival mechanism
- Replay is critical for a data platform: when we fix a bug in the PII detector, we need to reprocess all documents

### Ordering guarantees
- Kafka partitions guarantee ordering within a partition — we partition by document ID, ensuring all chunks of a document are processed in order
- SQS FIFO queues offer ordering but with throughput limitations (300 msg/s per group)

### Employer alignment
- Kafka appears in 3 of 6 target job descriptions (Easygo, CBA, AI startup)
- SQS does not appear in any
- Demonstrating Kafka expertise is a direct signal for $200k+ roles

### Observability
- Kafka exposes consumer lag, partition offsets, and throughput metrics natively
- Integrates cleanly with Prometheus + Grafana (our monitoring stack)

### Trade-offs accepted
- Kafka is more complex to operate than SQS — mitigated by using MSK Serverless (AWS manages brokers)
- MSK Serverless costs more than SQS for low-throughput workloads — acceptable for the skill signal and replay capability
- Local development requires running a Kafka broker via Docker Compose — already included in our dev environment

## Consequences

- We run Kafka in Docker Compose for local dev (KRaft mode, no Zookeeper)
- We use MSK Serverless in AWS (auto-scaling, minimal operational overhead)
- We gain message replay, ordering guarantees, and Kafka expertise signal
- Kafka UI is included in Docker Compose for local topic inspection

## References

- [Amazon MSK Serverless](https://aws.amazon.com/msk/features/msk-serverless/)
- [Kafka vs SQS comparison](https://aws.amazon.com/compare/the-difference-between-sqs-and-kafka/)
