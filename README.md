# RAG Q&A Engine

## Problem

Engineering teams drown in internal documentation — RFCs, ADRs, runbooks, Confluence pages. This system lets you ask natural-language questions over your own docs and get streamed, source-attributed answers.

## Quick Start

### Option A: Local Development (with Docker Postgres)

1. **Clone & setup:**
   ```bash
   git clone <repo>
   cd docsqa
   uv sync
   ```

2. **Start Postgres with pgvector:**
   ```bash
   docker run -d --name docsqa-postgres \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=postgres \
     -p 5432:5432 \
     pgvector/pgvector:pg17
   ```

3. **Set API credentials:**
   ```bash
   cp .env.example .env
   # Edit .env with ANTHROPIC_API_KEY, VOYAGE_API_KEY
   # DATABASE_URL is pre-configured for local Postgres
   ```

4. **Ingest documents:**
   ```bash
   mkdir -p docs
   # Add .md or .pdf files to docs/
   make ingest
   ```

5. **Start API:**
   ```bash
   make run
   ```

6. **Query:**
   ```bash
   make query Q="What is an ADR?"
   ```

### Option B: Production (Supabase)

See [MIGRATE_TO_SUPABASE.md](docs/MIGRATE_TO_SUPABASE.md) for migrating to Supabase pgvector.

## Architecture

```
┌─────────────┐
│  Documents  │
│ (.md, .pdf) │
└──────┬──────┘
       │ scripts/ingest.py
       ▼
   ┌────────────────────┐
   │ Chunking Strategy  │
   │ (500 tokens + 50   │
   │  token overlap)    │
   └────────┬───────────┘
            │
            ▼
   ┌────────────────────┐
   │  Voyage AI 3.5-lite│
   │  Embeddings        │
   │  (input_type:doc)  │
   └────────┬───────────┘
            │
            ▼
   ┌─────────────────────┐
   │  Postgres pgvector  │
   │  (ivfflat index)    │
   │  Local or Supabase  │
   └─────────┬───────────┘
             │
             │ retriever.py
             │
   ┌─────────────────────┐
   │  Query (FastAPI)    │
   │  POST /query        │
   │  Voyage Embed       │
   │  (input_type:query) │
   └────────┬────────────┘
            │
            ▼
   ┌─────────────────────┐
   │  Cosine Similarity  │
   │  (top-k retrieval)  │
   └────────┬────────────┘
            │
            ▼
   ┌────────────────────────┐
   │  Claude Haiku 4.5      │
   │  Stream Answer         │
   │  + Sources             │
   └─────────────────────────┘
```

## Eval Results

(Added after T5)

- **Total questions:** 20
- **Passed:** TBD
- **Score:** TBD
- **Precision@3:** TBD
- **MRR:** TBD
- **Avg cost/query:** TBD USD
- **Avg latency:** TBD ms

## Live Demo

(Added in T7)

## Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed local setup & troubleshooting
- **[Migrate to Supabase](docs/MIGRATE_TO_SUPABASE.md)** - Production database migration

## Next Steps

- **Reranking:** Add Voyage `rerank-2.5-lite` cross-encoder for top-5 refinement
- **Hybrid search:** Combine BM25 full-text search with vector similarity
- **Auth:** Add API key authentication for multi-user deployment

---

**Stack:** Python 3.12 | uv | FastAPI | Postgres pgvector | Voyage AI 3.5-lite | Anthropic Claude Haiku 4.5 | Docker
