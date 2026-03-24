# Operational Runbook

> Procedures for running, monitoring, and troubleshooting the RIPPAA AI Data Platform.

## Local Development

### First-time Setup

```bash
git clone https://github.com/rayan-noronha/rippaa-ai-data-platform.git
cd rippaa-ai-data-platform
make setup          # Creates venv, installs dependencies, sets up pre-commit
make infra-up       # Starts Kafka, PostgreSQL, LocalStack, Prometheus, Grafana
make seed-data      # Generates synthetic test documents
make run            # Starts the FastAPI server on http://localhost:8000
```

### Daily Development

```bash
make infra-up       # Start infrastructure (if not already running)
make run            # Start API server
make test           # Run tests before committing
make lint           # Check code quality
make check-all      # Run all quality checks (lint + type-check + security + tests)
```

### Local Service URLs

| Service | URL |
|---|---|
| API (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Kafka UI | http://localhost:8080 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/rippaa_dev) |
| LocalStack S3 | http://localhost:4566 |
| PostgreSQL | localhost:5432 (rippaa/rippaa_dev) |

## Troubleshooting

### PostgreSQL won't start
```bash
# Check if port 5432 is already in use
lsof -i :5432
# If another PostgreSQL is running, stop it or change the port in docker-compose.yml
```

### Kafka consumer lag increasing
```bash
# Check consumer group status
docker exec rippaa-kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group rippaa-processors
```

### pgvector index performance degrading
```sql
-- Check index size and usage
SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE schemaname = 'public';

-- Reindex if needed
REINDEX INDEX idx_chunks_embedding;
```

### Docker Compose services not healthy
```bash
make infra-logs     # Tail all service logs
docker compose -f infrastructure/docker/docker-compose.yml ps  # Check service status
make infra-down     # Nuclear option: stop everything and reset volumes
make infra-up       # Start fresh
```
