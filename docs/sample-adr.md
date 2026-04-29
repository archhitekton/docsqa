# ADR-001: Use Vector Embeddings for Document Retrieval

## Status
ACCEPTED

## Context
The engineering team needs a way to search through internal documentation quickly and accurately. Traditional full-text search using BM25 or PostgreSQL's built-in capabilities has limitations:
- Keyword matching misses semantic relevance
- Boolean queries are difficult for non-technical users
- Documents with different terminology but similar meaning are treated as unrelated

Vector embeddings solve this by representing documents in a high-dimensional space where semantic similarity is measured by proximity.

## Decision
We will use Voyage AI's `voyage-3.5-lite` embeddings model to power document retrieval in our RAG system. The model will embed document chunks at ingestion time and user queries at query time, with cosine similarity search via pgvector's IVFFlat index.

### Key Design Choices

1. **Embedding Model**: Voyage AI `voyage-3.5-lite`
   - Cost: $0.02 per 1M tokens (extremely cheap)
   - Performance: Outperforms OpenAI text-embedding-3-large by 6.34% on BEIR benchmark
   - Supports 32K context window
   - Provides `input_type` parameter to distinguish document vs query embeddings

2. **Vector Database**: PostgreSQL with pgvector extension
   - Leverages existing PostgreSQL infrastructure
   - IVFFlat index for fast approximate nearest neighbor search
   - Cosine similarity metric aligns with embedding space geometry
   - Hosted on Supabase (no local infrastructure needed)

3. **Chunking Strategy**
   - Fixed-size chunks of ~500 tokens
   - 50-token overlap to maintain context across chunk boundaries
   - Uses tiktoken's cl100k_base encoding for consistency

4. **Asymmetric Retrieval**
   - Documents: embed with `input_type="document"` (optimized for long-form text)
   - Queries: embed with `input_type="query"` (optimized for short-form questions)
   - Improves retrieval relevance through specialized representations

## Consequences

### Benefits
- Semantic search captures meaning beyond keywords
- Scales to large document sets (100K+ chunks)
- Low operational cost with Voyage AI
- Fast retrieval with IVFFlat index (sub-50ms for typical queries)

### Tradeoffs
- Requires external API calls for embeddings (Voyage AI)
- Embedding quality depends on model selection
- Vector storage adds database size (~4KB per 1024-dim embedding)
- No built-in semantic caching (each query generates new embeddings)

## Alternatives Considered

1. **OpenAI text-embedding-3-small**
   - More expensive ($0.02 per 1M tokens vs $0.002)
   - Slightly lower performance on benchmarks
   - Rejected: cost/performance tradeoff favors Voyage

2. **Cohere Embed**
   - Good performance, but less mature ecosystem
   - Rejected: Voyage has better benchmarks for this use case

3. **Local embeddings (all-MiniLM-L6-v2)**
   - Zero API costs
   - 16x smaller models (faster)
   - Rejected: significantly lower quality (MTEB: 42 vs 55)

## Implementation Timeline
- Week 1: Integrate Voyage embeddings into ingest pipeline
- Week 2: Benchmark retrieval quality on golden dataset
- Week 3: Optimize chunk size and overlap parameters
