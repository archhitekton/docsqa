# Setup Guide

## Prerequisites

- **Python 3.12+** (check with `python3 --version`)
- **uv** package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker & Docker Compose** ([install](https://docs.docker.com/get-docker/))
- **API Keys:**
  - Anthropic API key (from [console.anthropic.com](https://console.anthropic.com))
  - Voyage AI key (from [voyage.ai](https://voyage.ai))

## Local Development Setup (5 minutes)

### 1. Clone & Install Dependencies

```bash
git clone <repo>
cd docsqa
uv sync
```

This creates a virtual environment and installs all dependencies (81 packages).

### 2. Start Postgres with pgvector

```bash
make db-up
```

Or manually:
```bash
docker-compose up -d postgres
```

Verify:
```bash
docker-compose exec postgres pg_isready -U postgres
# Should return: accepting connections
```

### 3. Configure Credentials

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
ANTHROPIC_API_KEY="sk-ant-..."
VOYAGE_API_KEY="pa-..."
```

Database connection is pre-configured for local Postgres:
```
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
```

### 4. Verify Setup

Test database connection:
```bash
uv run python scripts/ingest.py --dry-run
```

Expected output:
```
✓ Ran migration: 001_init.sql
✓ DB connected
```

### 5. Add Documents

Create `docs/` directory and add files:
```bash
mkdir -p docs
# Add .md or .pdf files:
# docs/adr-001.md
# docs/runbook.pdf
```

### 6. Ingest Documents

```bash
make ingest
```

Output:
```
Ingested 42 chunks from adr-001.md
Ingested 150 chunks from runbook.pdf
```

### 7. Start API Server

```bash
make run
```

Runs on http://localhost:8000

### 8. Query

In another terminal:
```bash
make query Q="What are the main responsibilities?"
```

Or use curl:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this system about?"}'
```

## Troubleshooting

### Postgres won't start
```bash
# Check if port 5432 is already in use
lsof -i :5432

# Kill existing process or use different port in docker-compose.yml
```

### "type vector does not exist"
```bash
# pgvector extension not created. Restart:
make db-down
make db-up
uv run python scripts/ingest.py --dry-run
```

### Missing API keys
```bash
# Check .env file exists and has values:
cat .env | grep ANTHROPIC_API_KEY
# Should not be empty
```

### Out of memory during embedding
```bash
# Reduce batch size in app/embedder.py:
batch_size = 64  # Default is 128
```

## Next Steps

- Add your documentation to `docs/`
- Run `make ingest`
- Test with `make query Q="your question"`
- For production, see [MIGRATE_TO_SUPABASE.md](MIGRATE_TO_SUPABASE.md)

## Database Cleanup

To reset database (remove all ingested documents):
```bash
make db-down
make db-up
```

This removes the volume and starts fresh.
