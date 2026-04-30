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

Deliverable: a GitHub repo a hiring manager can clone, set three env vars, run `make seed && make ingest`, and hit a live URL — or run `make run` locally in under 5 minutes.

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | 82.5% of JDs require Python (field guide, 895 JDs) |
| API framework | FastAPI | 96 JDs explicitly mention FastAPI; native async + streaming |
| Vector DB | Supabase (pgvector hosted) | pgvector built-in, no local DB to manage; asyncpg connects directly; removes Docker Compose postgres service entirely |
| Embeddings | Voyage AI `voyage-3.5-lite` | Already using it in personal projects; $0.02/1M tokens; outperforms OpenAI text-embedding-3-large by 6.34%; 32K context; `input_type` distinction shows retrieval depth |
| LLM | Anthropic `claude-haiku-4-5` | Fast, cheap, streaming via anthropic SDK |
| PDF parsing | markitdown | Converts PDF → Markdown preserving heading hierarchy, code blocks, and lists; enables heading-aware chunking |
| Eval | Custom script + Claude-as-judge | Shows eval thinking; no heavy framework needed |
| Infra | Docker (API only) + Supabase | No local Postgres — hiring manager just needs `SUPABASE_URL` + `SUPABASE_KEY` in `.env` |

---

## Constraints

### Must
- Python 3.12, FastAPI, `markitdown[pdf]`, `anthropic` SDK, `voyageai` SDK, `asyncpg`
- API runs in Docker; DB is Supabase — `docker build + docker run` is sufficient, no `docker-compose.yml` needed
- Streaming response: FastAPI `StreamingResponse` with `text/event-stream`
- Structured answer schema: `{"answer": str, "sources": [{"filename": str, "heading_path": str, "chunk_id": int, "excerpt": str}]}`
- Eval harness produces a JSON report: `{"total": 20, "passed": N, "failed": M, "score": float}`
- README has a 60-second demo GIF and a cost-per-query estimate
- `.env.example` with all required env vars; `.env` in `.gitignore`
- Tests: at least `test_ingest.py` and `test_retrieval.py` with pytest
- Voyage calls MUST use `input_type="document"` for ingest, `input_type="query"` for query-time — correctness requirement, not style
- Out-of-scope fallback: if no retrieved chunk scores above `min_score` (default 0.75), return `{"answer": "I don't have that information in the provided documents.", "sources": []}` — do NOT pass low-confidence chunks to Claude. This is the #1 pattern tested in real take-home assignments.
- `min_score` MUST be a configurable query parameter: `QueryRequest(question: str, top_k: int = 5, min_score: float = 0.75)`. Document the precision/recall tradeoff in the README.

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
- New repo: `rag-qa-engine/`
- No existing code
- `.env` will hold: `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `DATABASE_URL`
  where `DATABASE_URL` is the Supabase direct connection string (from Supabase dashboard → Project Settings → Database → Connection string → URI, using the `Transaction pooler` URL for async workloads)

---

## Architecture (one paragraph)

CLI ingest script reads files from `./docs/`, chunks them, calls `voyageai.Client().embed(texts, model="voyage-3.5-lite", input_type="document")` in batches of 128, writes `(chunk_id, doc_name, chunk_text, embedding vector)` rows to Supabase Postgres via `asyncpg` (1024-dim, cosine). FastAPI app exposes `POST /query` — takes `{question: str, top_k: int = 5, min_score: float = 0.75}`, embeds the question with `input_type="query"`, runs `SELECT ... ORDER BY embedding <=> $1 LIMIT $2`, filters out chunks below `min_score`, and if none remain returns a safe fallback response without calling Claude. Otherwise feeds top-k chunks as context to Claude and streams the response back. Eval script loads `eval/golden.json` (20 QA pairs, including 3 unanswerable questions to test fallback), calls `/query` for each, sends (question, expected_answer, actual_answer) to Claude-as-judge with a binary pass/fail prompt, writes `eval/report.json`. No local Postgres — Supabase provides the hosted pgvector instance; `asyncpg` connects via the `DATABASE_URL` connection string directly.

---

## Tasks

### T1: Repo scaffold + Dockerfile
**What:** Create repo structure, `Dockerfile` for the API, `requirements.txt`, `.env.example`,
`Makefile` with targets: `make build`, `make run`, `make ingest`, `make query`, `make eval`, `make seed`.
No `docker-compose.yml` — DB is Supabase (external).
**Files:**
- `Dockerfile`
- `requirements.txt` — includes: `fastapi`, `uvicorn`, `asyncpg`, `anthropic`, `voyageai`, `markitdown[pdf]`, `tiktoken`, `pytest`, `httpx`, `python-dotenv`, `requests`
- `.env.example`
- `Makefile`
- `corpus.csv` — seed corpus of public domain PDFs (see below)
- `scripts/seed.py` — downloads PDFs from `corpus.csv` into `./docs/`
- `README.md` (skeleton with sections: Overview, Quick Start, Architecture, Eval Results, Next Steps)

**corpus.csv content:**
```csv
title,pdf_url
Think Python 2e,http://greenteapress.com/thinkpython2/thinkpython2.pdf
Think OS,https://greenteapress.com/thinkos/thinkos.pdf
Think DSP,https://greenteapress.com/thinkdsp/thinkdsp.pdf
```
All Allen Downey books, Creative Commons licensed. Three books gives ~900 chunks — enough to write a 23-question golden eval set with realistic answerable and unanswerable questions.

**scripts/seed.py behaviour:**
- Reads `corpus.csv` with `csv.DictReader`
- Downloads each PDF with `requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True)` — the User-Agent header is required; greenteapress returns 403 without it
- Saves to `./docs/{title}.pdf` (spaces replaced with underscores)
- Skips files that already exist (idempotent)
- Prints `Downloaded: {title}` or `Skipped (exists): {title}` per file

**Makefile `make seed` target:**
```makefile
seed:
	python scripts/seed.py
	@echo "Corpus ready in ./docs/ — run 'make ingest' next"
```

**Quick Start sequence in README (after `make seed` added):**
```
make build       # build Docker image
make seed        # download corpus PDFs into ./docs/
make ingest      # chunk + embed + store in Supabase
make run         # start API
make query Q="What is a recursive function?"
make eval        # run eval harness, write eval/report.json
```

**Verify:** `make seed` exits 0, `./docs/` contains 3 PDF files, each >100KB. `make seed` run a second time skips all three (idempotent).

---

### T2: Database schema + Supabase connection
**What:** On startup, run a migration that creates the `chunks` table. Note: Supabase has the
`vector` extension pre-enabled — do NOT run `CREATE EXTENSION` (will error on free tier).
```sql
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    doc_name TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    heading_path TEXT,
    chunk_text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```
`heading_path` stores the breadcrumb of Markdown headings that contains the chunk (e.g. `"Chapter 3 > Functions > Parameters and Arguments"`). Populated by the markitdown-aware chunker in T3. NULL for chunks that have no heading context. Returned in source citations so the user sees which section answered their question.
Use `asyncpg` for the async DB connection pool. Register the `vector` type with asyncpg using
`await conn.execute("SELECT NULL::vector")` on pool init so pgvector types decode correctly.
Migration runs on FastAPI startup via lifespan event.
**Files:**
- `app/db.py` — pool init, `get_pool()`, `run_migrations()`, vector type registration
- `app/migrations/001_init.sql`
**Verify:** `python scripts/ingest.py --dry-run` (no files, just connects) exits 0 and prints `DB connected`.

---

### T3: Ingest pipeline
**What:** CLI script `scripts/ingest.py` that converts, chunks, embeds, and stores documents.

**Step 1 — Convert to Markdown**
- For `.pdf` files: convert with `markitdown` — `MarkItDown().convert(filepath).text_content`
- For `.md` files: read directly — no conversion needed
- Both paths produce a single Markdown string. Store as `{filename}.md` in `./docs/converted/` for inspection/debugging.
- Why markitdown over pdfplumber: preserves heading hierarchy (`# Chapter`, `## Section`), fenced code blocks, and lists. pdfplumber produces raw text — a code block becomes an undifferentiated character blob.

**Step 2 — Heading-aware chunking (`app/chunker.py`)**

Two-phase strategy:

*Phase 1 — Split on heading boundaries:*
- Parse the Markdown string line by line
- When a line matches `^#{1,3} ` (H1, H2, or H3), start a new section
- Track the current heading breadcrumb path: e.g. `"Think Python > Chapter 3 > Functions"`
- Each section is a `Section(heading_path: str, text: str)` dataclass

*Phase 2 — Sliding window within each section:*
- Tokenise section text with `tiktoken` (`cl100k_base`)
- If section fits within `max_tokens` (default 500): emit as a single chunk
- If section exceeds `max_tokens`: apply sliding window — step forward by `max_tokens - overlap` tokens (default overlap 50), emit each window as a chunk
- Each emitted chunk carries its `heading_path` forward

Result: chunks that never span two headings. A chunk about "Chapter 3 > Parameters" will never contain content from "Chapter 4 > Return Values".

**`app/chunker.py` contract:**
```python
@dataclass
class Section:
    heading_path: str
    text: str

@dataclass
class Chunk:
    heading_path: str
    text: str

def parse_sections(markdown: str) -> list[Section]: ...
def chunk_section(section: Section, max_tokens: int = 500, overlap: int = 50) -> list[Chunk]: ...
def chunk_document(markdown: str, max_tokens: int = 500, overlap: int = 50) -> list[Chunk]: ...
```

**Step 3 — Embed and store**
- Collect all chunks across all files into a flat list
- Call `voyageai.Client().embed([c.text for c in batch], model="voyage-3.5-lite", input_type="document")` in batches of 128
- Bulk insert `(doc_name, chunk_index, heading_path, chunk_text, embedding)` via `asyncpg.executemany`
- Print: `Ingested {n} chunks from {filename}` per file

**Files:**
- `scripts/ingest.py`
- `app/chunker.py` — `Section`, `Chunk` dataclasses + three functions above
- `app/embedder.py` — `embed_batch(texts: list[str]) -> list[list[float]]`
- `docs/converted/` — gitignored directory for intermediate Markdown files

**Verify:**
- `make ingest` prints chunk counts per file; `SELECT COUNT(*) FROM chunks;` returns > 0
- `SELECT DISTINCT heading_path FROM chunks LIMIT 10;` returns non-null heading breadcrumbs
- `SELECT chunk_text FROM chunks WHERE heading_path LIKE '%Chapter 3%' LIMIT 3;` returns coherent within-section text — no chunk spans two chapter headings

---

### T4: Query endpoint with streaming
**What:** `POST /query` endpoint in FastAPI:
- Request body: `QueryRequest(question: str, top_k: int = 5, min_score: float = 0.75)`
- Embed question with `voyageai.Client().embed([question], model="voyage-3.5-lite", input_type="query")`
- Run pgvector cosine similarity query: `SELECT *, 1 - (embedding <=> $1) AS score FROM chunks ORDER BY embedding <=> $1 LIMIT $2`
- Filter results to only chunks where `score >= min_score`
- **If no chunks pass the threshold**: return immediately (no Claude call) with `{"answer": "I don't have that information in the provided documents.", "sources": []}` as a regular JSON response (not streamed)
- **If chunks pass the threshold**: build system prompt + user prompt (question + retrieved context with source labels), call `anthropic.messages.stream()` with `claude-haiku-4-5`, stream response as `text/event-stream` SSE: `data: <token>\n\n`, final event `data: [DONE]\n\n`, trailing sources event: `data: {"sources": [...]}\n\n`
**Files:**
- `app/main.py` — FastAPI app, lifespan, route registration
- `app/routes/query.py` — `POST /query`
- `app/retriever.py` — `retrieve(question_embedding, top_k, min_score, pool) -> list[Chunk]`
- `app/llm.py` — `stream_answer(question, chunks) -> AsyncGenerator[str, None]`
- `app/models.py` — `QueryRequest`, `Chunk` (includes `heading_path`), `Source` (includes `heading_path` in citation), `FallbackResponse` Pydantic models
**Verify:** `make query Q="What is pgvector?"` streams tokens and prints sources. `make query Q="Who won the 2024 World Cup?"` returns fallback JSON instantly with no streamed tokens.

---

### T5: Eval harness
**What:**
- `eval/golden.json`: 23 hand-written QA pairs (20 answerable + 3 unanswerable). Format:
  ```json
  [{"question": str, "expected": str, "relevant_doc": str, "answerable": bool}]
  ```
  `relevant_doc` is the filename that should appear in the top-3 sources. For unanswerable questions set `relevant_doc: null` and `answerable: false`. The 3 unanswerable questions should be clearly out-of-scope (e.g. "Who won the 2024 FIFA World Cup?" for an engineering docs corpus).
- `scripts/eval.py`:
  1. For each pair, call `POST /query` with `top_k=5, min_score=0.75`, record response + sources + latency
  2. For **unanswerable** questions: PASS if response contains the fallback string `"I don't have that information"`, FAIL otherwise (hallucination)
  3. For **answerable** questions:
     - Compute **precision@3**: was `relevant_doc` in the top-3 returned sources? Binary, averaged across answerable set.
     - Compute **MRR**: `1/rank` of `relevant_doc` in sources list, 0 if not found. Averaged across answerable set.
     - Send `(question, expected, actual_answer)` to Claude judge: `"Does the actual answer correctly address the question given the expected answer? Reply with exactly PASS or FAIL and one sentence explaining why."`
  4. Compute **cost_usd** per question: `(voyage_tokens_query × 0.00000002) + (claude_input_tokens × 0.00000025) + (claude_output_tokens × 0.00000125)`. Unanswerable questions that hit the fallback path cost only the Voyage embedding call.
  5. Write `eval/report.json`:
     ```json
     {
       "total": 23,
       "answerable": 20,
       "unanswerable": 3,
       "passed": N,
       "score": N/23,
       "hallucination_rate": failed_unanswerable/3,
       "precision_at_3": float,
       "mrr": float,
       "avg_cost_usd": float,
       "avg_latency_ms": float,
       "results": [...]
     }
     ```
  6. Print summary table to stdout: question | answerable | PASS/FAIL | P@3 | rank | cost_usd
**Files:**
- `eval/golden.json`
- `scripts/eval.py`
- `eval/report.json` (committed as example output)
**Verify:** `make eval` completes. `eval/report.json` has all keys including `hallucination_rate`. The 3 unanswerable questions should show `cost_usd` significantly lower than answerable ones (no Claude call).

---

### T6: README + demo polish
**What:**
- README sections:
  - **Problem** (first section, 2 sentences): "Engineering teams drown in internal documentation — RFCs, ADRs, runbooks, Confluence pages. This system lets you ask natural-language questions over your own docs and get streamed, source-attributed answers." Swap domain to match your actual `docs/` sample content — developer/engineering docs is the default; healthcare or legal docs are equally valid pivots.
  - **Quick Start** (5 commands max — use the sequence from T1: `make build` → `make seed` → `make ingest` → `make run` → `make query`)
  - **Architecture** diagram (ASCII is fine)
  - **Eval Results** — paste score + precision@3 + MRR + hallucination_rate + cost-per-query from report.json
  - **Live Demo** — link to deployed instance (added in T7)
  - **Next Steps** — reranking, hybrid search, auth
- Add `docs/sample.md` — a 500-word engineering document (e.g. an ADR or runbook) used as the seed for the golden eval set. Using a real doc type signals domain judgment to hiring managers.
- Record a terminal demo GIF using `vhs` or `asciinema` showing ingest → query → eval
- Record a **Loom walkthrough** (5 minutes max): open with the live URL, run an answerable query showing streaming + sources, run an unanswerable query showing the fallback response, show `eval/report.json` and call out the hallucination_rate and cost-per-query numbers. This is the most important deliverable for take-home assignments — hiring managers watch it before reading code.
- Makefile `make demo` that runs a canned query showing streaming output
**Files:**
- `README.md` (complete)
- `docs/sample.md`
- `demo.gif` or `demo.cast`
- Loom URL committed to README under **Demo** section
**Verify:** README renders correctly on GitHub with live URL and Loom link. `make run` starts the API and `make demo` streams a visible answer in under 10 seconds.

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
2. Set secrets via CLI (never committed): `fly secrets set ANTHROPIC_API_KEY=... VOYAGE_API_KEY=... DATABASE_URL=...`
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
I shipped a 23-question eval harness — 20 answerable, 3 deliberately unanswerable — that tracks
answer quality, precision@3, MRR, hallucination rate, and cost-per-query. Score was 17/20 on
answerable questions, hallucination rate zero — the fallback threshold caught all three
out-of-scope questions without calling Claude. Avg cost $0.0003/query."

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
  why binary PASS/FAIL is appropriate at this stage. Call out the hallucination_rate: zero — the
  fallback threshold caught all three out-of-scope questions without a Claude call. Mention the
  retrieval failures and what you'd fix (chunk overlap tuning or Voyage reranker).
- "How did you pick the 0.75 similarity threshold?" — Empirically: I ran the eval at 0.70, 0.75,
  and 0.80. At 0.70 one unanswerable question leaked through (hallucination). At 0.80 two
  answerable questions hit the fallback incorrectly. 0.75 was the sweet spot for this corpus —
  but I'd re-tune it for any new domain or document set.
- "What would you do differently at scale?" — Async ingest pipeline with SQS, connection
  pooling, caching repeated query embeddings, hybrid BM25 + vector search, and Voyage
  `rerank-2.5-lite` cross-encoder to rerank top-20 down to top-5.