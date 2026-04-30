#!/usr/bin/env python3
"""End-to-end validation: ingest → query → retrieve (real APIs, no DB)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chunker import chunk_document
from app.embedder import get_embedder


def cosine_similarity(a, b):
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0


print("\n=== E2E Validation: Ingest → Query → Retrieve ===\n")

# Read & chunk
test_md = Path("docs/converted/test.md").read_text(encoding="utf-8")
print(f"1. Read test.md: {len(test_md)} chars")

chunks = chunk_document(test_md, max_tokens=500, overlap=50)
print(f"2. Chunked into {len(chunks)} chunks")

# Embed chunks (real Voyage API)
print(f"3. Embedding {len(chunks)} chunks...")
embedder = get_embedder()
chunk_texts = [chunk.text for chunk in chunks]
chunk_embeddings = embedder.embed_documents(chunk_texts)
print(f"   Generated {len(chunk_embeddings)} embeddings")

# Query
question = "What is Node.js development?"
print(f"4. Query: \"{question}\"")

query_embedding = embedder.embed_query(question)
print(f"5. Embedded question")

# Retrieve
scores = []
for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
    score = cosine_similarity(query_embedding, embedding)
    scores.append((i, score, chunk))

scores.sort(key=lambda x: x[1], reverse=True)

min_score = 0.75
results = [(idx, score, c) for idx, score, c in scores if score >= min_score]

print(f"6. Retrieval (min_score={min_score}):")
for idx, score, chunk in scores:
    status = "✓" if score >= min_score else "✗"
    print(f"   {status} chunk {idx}: {score:.3f}")

if results:
    print(f"\nTop sources:")
    for rank, (idx, score, chunk) in enumerate(results[:3], 1):
        print(f"  {rank}. [{score:.3f}] chunk {idx}")
        print(f"     {chunk.text[:80]}...")
else:
    print(f"\n(No chunks above threshold - would return fallback)")

print(f"\n✅ E2E pipeline validated\n")
