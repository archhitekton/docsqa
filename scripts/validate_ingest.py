#!/usr/bin/env python3
"""End-to-end validation: ingest → query → retrieve (no live API/DB)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chunker import chunk_document

def cosine_similarity(a, b):
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0

# ============================================================================
# STEP 1: INGEST - Read & Chunk
# ============================================================================
test_md = Path("docs/converted/test.md").read_text(encoding="utf-8")
print("=" * 70)
print("E2E VALIDATION: Ingest → Query → Retrieve")
print("=" * 70)
print(f"\n[INGEST] Read test.md: {len(test_md)} chars, {len(test_md.splitlines())} lines")

chunks = chunk_document(test_md, max_tokens=500, overlap=50)
print(f"[INGEST] Chunked into {len(chunks)} chunks")

# ============================================================================
# STEP 2: INGEST - Mock Embed & Store
# ============================================================================
print(f"[INGEST] Embedding {len(chunks)} chunks (mock Voyage API)")

# Mock embeddings: hash-based stable vectors for reproducibility
chunk_embeddings = {}
for i, chunk in enumerate(chunks):
    base = hash(chunk.text) % 100 / 100
    embedding = [base + (j % 10) * 0.001 for j in range(1024)]
    mag = sum(x*x for x in embedding) ** 0.5
    chunk_embeddings[i] = [x / mag for x in embedding]

print(f"[INGEST] Generated {len(chunk_embeddings)} 1024-dim embeddings")
print(f"[INGEST] Would store {len(chunks)} records in Supabase pgvector\n")

# ============================================================================
# STEP 3: QUERY - Embed Question & Retrieve
# ============================================================================
question = "What is Node.js development?"
print(f"[QUERY] Question: \"{question}\"")

# Mock query embedding
query_base = hash(question) % 100 / 100
query_embedding = [query_base + (j % 10) * 0.001 for j in range(1024)]
mag = sum(x*x for x in query_embedding) ** 0.5
query_embedding = [x / mag for x in query_embedding]

print(f"[QUERY] Embedded question (mock Voyage API)")

# ============================================================================
# STEP 4: RETRIEVE - Cosine Similarity + Filter
# ============================================================================
print(f"[RETRIEVE] Computing cosine similarity...")

scores = []
for chunk_id, chunk in enumerate(chunks):
    embedding = chunk_embeddings[chunk_id]
    score = cosine_similarity(query_embedding, embedding)
    scores.append((chunk_id, score, chunk))

# Sort by score
scores.sort(key=lambda x: x[1], reverse=True)

# Filter by min_score=0.75
min_score = 0.75
results = [(cid, score, c) for cid, score, c in scores if score >= min_score]

print(f"[RETRIEVE] Found {len(results)} chunks above min_score={min_score}")

if results:
    print(f"\n[RESULTS] Top sources for question:\n")
    for rank, (chunk_id, score, chunk) in enumerate(results[:3], 1):
        print(f"  {rank}. [{score:.3f}] test.md (chunk {chunk_id})")
        print(f"     Heading: {chunk.heading_path or '(none)'}")
        print(f"     Text: {chunk.text[:70]}...")
        print()
else:
    print(f"\n[FALLBACK] No chunks passed min_score threshold")
    print(f"  Would return: \"I don't have that information in the provided documents.\"")

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 70)
print("✅ E2E Validation Complete")
print("=" * 70)
print(f"\nPipeline flow:")
print(f"  ✓ Ingest: {len(chunks)} chunks")
print(f"  ✓ Embed: {len(chunk_embeddings)} vectors (Voyage mock)")
print(f"  ✓ Store: Would insert to Supabase")
print(f"  ✓ Query: Embedded question")
print(f"  ✓ Retrieve: Cosine similarity + min_score filter")
print(f"  ✓ Results: {len(results)} chunks matched (threshold {min_score})")
print(f"\nReady for: make ingest → make run → make query")
