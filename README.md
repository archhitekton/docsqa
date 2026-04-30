# RAG Q&A Engine

## Problem

Engineering teams drown in internal documentation — RFCs, ADRs, runbooks, Confluence pages. This system lets you ask natural-language questions over your own docs and get streamed, source-attributed answers.

## Quick Start

```bash
make build       # Build Docker image
make seed        # Download corpus PDFs into ./docs/
make ingest      # Chunk, embed, and store in Supabase
make run         # Start API on localhost:8000
make query Q="What is a recursive function?"
```

## Architecture

```
Documents (PDF/Markdown)
        ↓
   [Convert to Markdown]
        ↓
[Heading-aware Chunking] ← heading_path breadcrumbs
        ↓
[Voyage AI Embeddings] ← input_type="document"
        ↓
[Supabase pgvector] ← 1024-dim, cosine similarity
        ↓
[Query Embedding] ← input_type="query"
        ↓
[Retrieval + Filter] ← min_score threshold
        ↓
[Claude Streaming] ← structured answer + sources
        ↓
[FastAPI Response] ← SSE format
```

## Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Industry standard for AI engineering |
| API | FastAPI | Native async + streaming support |
| Vector DB | Supabase (pgvector) | Hosted, zero ops, asyncpg integration |
| Embeddings | Voyage AI `voyage-3.5-lite` | Document/query input_type distinction |
| LLM | Claude Haiku 4.5 | Fast, cheap, streaming |
| PDF parsing | markitdown | Preserves heading hierarchy and structure |
| Eval | Custom script + Claude-as-judge | No heavy framework needed |

## Eval Results

*(Results added after T5 completion)*

- **Score**: N/23 questions correct
- **Hallucination Rate**: N/3 out-of-scope questions rejected
- **Precision@3**: N%
- **MRR**: N
- **Cost/Query**: $N

## Live Demo

*(URL added in T7 after Fly.io deployment)*

## Loom Walkthrough

*(Video link added in T6)*

## Next Steps

- Reranking (Voyage `rerank-2.5-lite` cross-encoder)
- Hybrid search (BM25 + vector)
- Query rewriting / HyDE
- Multi-user auth
