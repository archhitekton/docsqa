# RAG Q&A Engine — Portfolio Project 01

## Why

Demonstrate production AI engineering depth to Sydney hiring managers: not a notebook demo,
but a working system with real chunking tradeoffs, eval harness, and Docker deployment.
RAG appears in 35.9% of all AI engineering JDs — the most common pattern in the dataset.

---

## What

A document Q&A API that:
- Ingests Markdown and PDF files via CLI ingest script
- Chunks documents with configurable strategy (fixed-size + sentence-aware overlap)
- Embeds chunks using Voyage AI `voyage-3.5-lite` and stores in Supabase pgvector
- Retrieves top-k chunks via cosine similarity + optional metadata filter
- Streams answers via FastAPI endpoint using Anthropic Claude (structured output: answer + sources)
- Ships an eval harness: golden QA dataset (20 pairs), LLM-as-judge scorer, pass/fail report

Deliverable: a GitHub repo a hiring manager can clone, set three env vars, and hit a live URL — or run `make run` locally in under 5 minutes.

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | 82.5% of JDs require Python (field guide, 895 JDs) |
| Dependency management | `uv` | Fast, deterministic Python package manager; handles both deps and venv |
| API framework | FastAPI | 96 JDs explicitly mention FastAPI; native async + streaming |
| Vector DB | Supabase (pgvector hosted) | pgvector built-in, no local DB to manage; asyncpg connects directly; removes Docker Compose postgres service entirely |
| Embeddings | Voyage AI `voyage-3.5-lite` | Already using it in personal projects; $0.02/1M tokens; outperforms OpenAI text-embedding-3-large by 6.34%; 32K context; `input_type` distinction shows retrieval depth |
| LLM | Anthropic `claude-haiku-4-5` | Fast, cheap, streaming via anthropic SDK |
| PDF parsing | pdfplumber | Pure Python, no Java dependency |
| Eval | Custom script + Claude-as-judge | Shows eval thinking; no heavy framework needed |
| Infra | Docker (API only) + Supabase | No local Postgres — hiring manager just needs `SUPABASE_URL` + `SUPABASE_KEY` + `ANTHROPIC_API_KEY` + `VOYAGE_API_KEY` in `.env` |

---

## Constraints

### Must
- Python 3.12, FastAPI, pdfplumber, `anthropic` SDK, `voyageai` SDK, `asyncpg`
- Use `uv` for dependency management and venv setup: `pyproject.toml` + `uv.lock`
- API runs in Docker; DB is Supabase — `docker build + docker run` is sufficient, no `docker-compose.yml` needed
- Streaming response: FastAPI `StreamingResponse` with `text/event-stream`
- Structured answer schema: `{"answer": str, "sources": [{"filename": str, "chunk_id": int, "excerpt": str}]}`
- Eval harness produces a JSON report: `{"total": 20, "passed": N, "failed": M, "score": float}`
- README has a 60-second demo GIF and a cost-per-query estimate
- `.env.example` with all required env vars; `.env` in `.gitignore`
- Tests: at least `test_ingest.py` and `test_retrieval.py` with pytest
- Voyage calls MUST use `input_type="document"` for ingest, `input_type="query"` for query-time — correctness requirement, not style
- Credentials: source `~/.claude/credentials/credentials.env` for API keys (see CLAUDE.md)

### Must Not
- No LangChain, LlamaIndex, or any orchestration framework — raw SDK calls only.
  Reason: shows you understand the fundamentals, not just the wrapper.
- No frontend — API only. A Makefile target that runs `curl` demos is sufficient.
- No fine-tuning, no self-hosted model, no GPU requirement
- No auth, no multi-tenancy, no user accounts — out of scope for portfolio demo
- No Kubernetes, no local Postgres container — Supabase is the DB
- No Pinecone, Weaviate, Chroma — Supabase pgvector only

### Out of Scope
- Reranking (cross-encoder) — mention in README as "next step"
- Hybrid search (BM25 + vector) — mention as "next step"
- Query rewriting / HyDE
- Streaming tokens to a UI
- Multi-user or production auth

---

## Current State
- New repo: `rag-qa-engine/` (or use existing `docsqa/` root)
- No existing code
- API keys: `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` in `~/.claude/credentials/credentials.env` (see CLAUDE.md for setup)
- `.env` will hold: sourced from credentials, plus `DATABASE_URL` (Supabase direct connection string from dashboard → Project Settings → Database → Connection string → URI, using the `Transaction pooler` URL for async workloads)

---

## Architecture (one paragraph)

CLI ingest script reads files from `./docs/`, chunks them, calls `voyageai.Client().embed(texts, model="voyage-3.5-lite", input_type="document")` in batches of 128, writes `(chunk_id, doc_name, chunk_text, embedding vector)` rows to Supabase Postgres via `asyncpg` (1024-dim, cosine). FastAPI app exposes `POST /query` — takes `{question: str, top_k: int = 5}`, embeds the question with `input_type="query"`, runs `SELECT ... ORDER BY embedding <=> $1 LIMIT $2`, feeds top-k chunks as context to Claude, streams the response back. Eval script loads `eval/golden.json` (20 QA pairs), calls `/query` for each, sends (question, expected_answer, actual_answer) to Claude-as-judge with a binary pass/fail prompt, writes `eval/report.json`. No local Postgres — Supabase provides the hosted pgvector instance; `asyncpg` connects via the `DATABASE_URL` connection string directly.

---

## Tasks

### T1: Repo scaffold + Dockerfile
**What:** Create repo structure, `Dockerfile` for the API, `pyproject.toml` (uv-managed), `.env.example`,
`Makefile` with targets: `make build`, `make run`, `make ingest`, `make query`, `make eval`.
No `docker-compose.yml` — DB is Supabase (external).
**Files:**
- `Dockerfile` — uses `uv pip install` to install from `pyproject.toml`
- `pyproject.toml` — uv project config with dependencies: `fastapi`, `uvicorn`, `asyncpg`, `anthropic`, `voyageai`, `pdfplumber`, `tiktoken`, `pytest`, `httpx`, `python-dotenv`
- `uv.lock` — lockfile (auto-generated by uv)
- `.env.example`
- `Makefile`
- `README.md` (skeleton with sections: Overview, Quick Start, Architecture, Eval Results, Next Steps)
**Verify:** `make build` exits 0; `docker run --env-file .env rag-qa-engine python -c "import anthropic, voyageai, asyncpg"` exits 0.

---

### T2: Database schema + Supabase connection
**What:** On startup, run a migration that creates the `chunks` table. Credentials loaded from `~/.claude/credentials/credentials.env` (see CLAUDE.md).
Note: Supabase has the `vector` extension pre-enabled — do NOT run `CREATE EXTENSION` (will error on free tier).
```sql
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    doc_name TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```
Use `asyncpg` for the async DB connection pool. Register the `vector` type with asyncpg using
`await conn.execute("SELECT NULL::vector")` on pool init so pgvector types decode correctly.
Migration runs on FastAPI startup via lifespan event.
**Files:**
- `app/db.py` — pool init, `get_pool()`, `run_migrations()`, vector type registration
- `app/migrations/001_init.sql`
**Verify:** `uv run python scripts/ingest.py --dry-run` (no files, just connects) exits 0 and prints `DB connected`.

---

### T3: Ingest pipeline
**What:** CLI script `scripts/ingest.py` that:
1. Walks `./docs/` for `.md` and `.pdf` files
2. For `.md`: splits on `\n\n`, then merges into chunks of ~500 tokens with 50-token overlap
3. For `.pdf`: uses `pdfplumber` page by page, then same chunking
4. Token counting: use `tiktoken` with `cl100k_base` (approximate — Voyage tokeniser differs but this is close enough for chunking)
5. Calls `voyageai.Client().embed(batch, model="voyage-3.5-lite", input_type="document")` in batches of 128
6. Bulk inserts into `chunks` table via `asyncpg.executemany`
7. Prints: `Ingested {n} chunks from {filename}` per file
**Files:**
- `scripts/ingest.py`
- `app/chunker.py` — `chunk_text(text: str, max_tokens: int, overlap: int) -> list[str]`
- `app/embedder.py` — `embed_batch(texts: list[str]) -> list[list[float]]`
**Verify:** `make ingest` with sample docs in `./docs/` prints chunk counts; `SELECT COUNT(*) FROM chunks;` returns > 0.

---

### T4: Query endpoint with streaming
**What:** `POST /query` endpoint in FastAPI:
- Request body: `QueryRequest(question: str, top_k: int = 5)`
- Embed question with `voyageai.Client().embed([question], model="voyage-3.5-lite", input_type="query")`
- Run pgvector cosine similarity query to fetch `top_k` chunks
- Build system prompt + user prompt (question + retrieved context with source labels)
- Call `anthropic.messages.stream()` with `claude-haiku-4-5`
- Stream response as `text/event-stream` SSE: `data: <token>\n\n`, final event `data: [DONE]\n\n`
- After streaming completes, return sources as a trailing JSON event: `data: {"sources": [...]}\n\n`
**Files:**
- `app/main.py` — FastAPI app, lifespan, route registration
- `app/routes/query.py` — `POST /query`
- `app/retriever.py` — `retrieve(question_embedding, top_k, pool) -> list[Chunk]`
- `app/llm.py` — `stream_answer(question, chunks) -> AsyncGenerator[str, None]`
- `app/models.py` — `QueryRequest`, `Chunk`, `Source` Pydantic models
**Verify:** `make query Q="What is pgvector?"` streams tokens to stdout and prints sources JSON at end. (Makefile uses `uv run` internally.)

---

### T5: Eval harness
**What:**
- `eval/golden.json`: 20 hand-written QA pairs. Format:
  ```json
  [{"question": str, "expected": str, "relevant_doc": str}]
  ```
  `relevant_doc` is the filename that should appear in the top-3 sources for that question. Used to compute precision@k without a separate relevance judge.
- `scripts/eval.py`:
  1. For each pair, call `POST /query` with `top_k=5`, record response + sources + latency
  2. Compute **precision@3**: was `relevant_doc` in the top-3 returned sources? Binary per question, averaged across all 20.
  3. Compute **MRR** (Mean Reciprocal Rank): `1/rank` of `relevant_doc` in the returned sources list, averaged across all 20. If not found, score is 0.
  4. Send `(question, expected, actual_answer)` to Claude judge prompt:
     `"Does the actual answer correctly address the question given the expected answer? Reply with exactly PASS or FAIL and one sentence explaining why."`
  5. Compute **cost_usd** per question: `(voyage_tokens_query × 0.00000002) + (claude_input_tokens × 0.00000025) + (claude_output_tokens × 0.00000125)`. Sum and average across all 20.
  6. Write `eval/report.json`:
     ```json
     {
       "total": 20,
       "passed": N,
       "score": N/20,
       "precision_at_3": float,
       "mrr": float,
       "avg_cost_usd": float,
       "avg_latency_ms": float,
       "results": [...]
     }
     ```
  7. Print summary table to stdout: question | PASS/FAIL | P@3 | rank | cost_usd
**Files:**
- `eval/golden.json`
- `scripts/eval.py`
- `eval/report.json` (committed as example output)
**Verify:** `make eval` completes, `eval/report.json` exists with all six top-level keys, summary table printed to stdout. (Makefile uses `uv run` internally.)

---

### T6: README + demo polish
**What:**
- README sections:
  - **Problem** (first section, 2 sentences): "Engineering teams drown in internal documentation — RFCs, ADRs, runbooks, Confluence pages. This system lets you ask natural-language questions over your own docs and get streamed, source-attributed answers." Swap domain to match your actual `docs/` sample content — developer/engineering docs is the default; healthcare or legal docs are equally valid pivots.
  - **Quick Start** (5 commands max, note: use `uv sync` to install deps, `uv run python` to execute)
  - **Architecture** diagram (ASCII is fine)
  - **Eval Results** — paste score + precision@3 + MRR + cost-per-query from report.json
  - **Live Demo** — link to deployed instance (added in T7)
  - **Next Steps** — reranking, hybrid search, auth
- Add `docs/sample.md` — a 500-word engineering document (e.g. an ADR or runbook) used as the seed for the golden eval set. Using a real doc type signals domain judgment to hiring managers.
- Record a terminal demo GIF using `vhs` or `asciinema` showing ingest → query → eval
- Makefile `make demo` that runs a canned query showing streaming output
**Files:**
- `README.md` (complete)
- `docs/sample.md`
- `demo.gif` or `demo.cast`
**Verify:** README renders correctly on GitHub; `make run` starts the API and `make demo` streams a visible answer in under 10 seconds.

---

### T7: Deploy to Fly.io
**What:** Deploy the FastAPI container as a public live demo so the README has a real URL.
Fly.io free tier is sufficient — 256MB RAM, shared CPU, always-on.
1. Add `fly.toml` to repo root:
   ```toml
   app = "rag-qa-engine"
   primary_region = "syd"

   [build]

   [http_service]
     internal_port = 8000
     force_https = true
     auto_stop_machines = "stop"
     auto_start_machines = true
     min_machines_running = 0
   ```
2. Set secrets via CLI (never committed): `fly secrets set ANTHROPIC_API_KEY=... VOYAGE_API_KEY=... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...`
3. Add `make deploy` target: `fly deploy`
4. Add `GET /health` endpoint to `app/main.py` returning `{"status": "ok", "model": "voyage-3.5-lite"}` — used by Fly health checks and shows at the live URL root.
5. Update README: replace placeholder with real Fly URL in the **Live Demo** section.

**Files:**
- `fly.toml`
- `app/main.py` — add `GET /health`
- `Makefile` — add `make deploy`
- `README.md` — live URL added

**Verify:** `curl https://rag-qa-engine.fly.dev/health` returns `{"status": "ok", ...}` with HTTP 200. `curl -X POST https://rag-qa-engine.fly.dev/query -d '{"question":"test"}' -H 'Content-Type: application/json'` streams a response.

---



**The 60-second version:**
"I built a document Q&A engine from scratch — no LangChain, raw Voyage AI and Anthropic SDKs.
Supabase hosts the pgvector instance, FastAPI streams responses, it's live on Fly.io right now.
I shipped a 20-question eval harness that tracks answer quality, precision@3, MRR, and
cost-per-query. Score was 17/20, precision@3 was 0.85, avg cost $0.0003/query.
The three retrieval misses all came from questions that needed information across multiple
chunks — I documented that as the reranking gap and it's in the Next Steps."

**Trade-off questions you'll get:**
- "Why voyage-3.5-lite over the full voyage-3.5?" — At $0.02/1M tokens it's the same price as
  voyage-3-lite but 4.28% better retrieval quality. For a portfolio RAG project the latency and
  cost savings matter more than the ~2% quality gap vs voyage-3.5. I'd step up to voyage-3.5 or
  voyage-3-large if I were building a domain-specific system where retrieval precision is critical.
- "Why Voyage over OpenAI embeddings?" — Anthropic's recommended partner. voyage-3.5-lite
  outperforms OpenAI text-embedding-3-large by 6.34% on retrieval benchmarks. Also: Voyage has a
  proper `input_type` distinction — `document` for ingest, `query` for retrieval. OpenAI doesn't
  have this, which means their embeddings aren't optimised for asymmetric retrieval.
- "Why Supabase over a local Postgres?" — Removes the local DB dependency entirely. Anyone can
  clone and run this with three env vars and no Docker Compose. At scale I'd evaluate
  Supabase's pgvector performance vs a dedicated Postgres instance, but for a portfolio demo
  it's the right call — zero ops overhead.
- "Why not LangChain?" — Raw SDKs show you understand retrieval primitives. LangChain abstracts
  chunking strategy, embedding batching, and retrieval scoring. In production you tune all three.
- "How do you know it works?" — Point to eval/report.json. Walk through the judge prompt and
  why binary PASS/FAIL is appropriate at this stage. Mention the two failure cases and what
  you'd fix (chunk overlap tuning or adding a Voyage reranker as a second pass).
- "What would you do differently at scale?" — Async ingest pipeline with SQS, connection
  pooling, caching repeated query embeddings, hybrid BM25 + vector search, and Voyage
  `rerank-2.5-lite` cross-encoder to rerank top-20 down to top-5.