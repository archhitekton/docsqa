#!/usr/bin/env python3
"""End-to-end pipeline demo with test.md."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chunker import chunk_document

def cosine_similarity(a, b):
    """Simple cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0

# Step 1: Convert & Read
print("=" * 60)
print("DEMO: RAG Pipeline End-to-End")
print("=" * 60)

test_md = Path("docs/converted/test.md").read_text()
print(f"\n[STEP 1] Convert PDF → Markdown")
print(f"  Read test.md: {len(test_md)} chars")

# Step 2: Chunk
chunks = chunk_document(test_md, max_tokens=500, overlap=50)
print(f"\n[STEP 2] Chunk Markdown")
print(f"  Generated {len(chunks)} chunks with heading-aware strategy:")
for i, chunk in enumerate(chunks):
    print(f"    {i+1}. {chunk.heading_path} ({len(chunk.text)} chars)")

# Step 3: Mock Embeddings
print(f"\n[STEP 3] Embed (Voyage AI) - MOCKED")
embeddings = {}
for i, chunk in enumerate(chunks):
    # Mock embedding: hash-based stable vector
    base = hash(chunk.text) % 100 / 100
    embedding = [base + (j % 10) * 0.001 for j in range(1024)]
    embeddings[i] = embedding
    # Normalize
    mag = sum(x*x for x in embedding) ** 0.5
    embeddings[i] = [x / mag for x in embedding]

print(f"  Generated {len(embeddings)} 1024-dim embeddings")

# Step 4: Simulate Database Storage
print(f"\n[STEP 4] Store in Database (Supabase pgvector) - SIMULATED")
db = {}
for i, (chunk, emb) in enumerate(zip(chunks, embeddings.values())):
    db[i] = {
        "doc_name": "test.md",
        "chunk_index": i,
        "heading_path": chunk.heading_path,
        "chunk_text": chunk.text,
        "embedding": emb,
    }
print(f"  Stored {len(db)} records")

# Step 5: Query & Retrieve
print(f"\n[STEP 5] Query & Retrieve")
query = "What is a function?"
print(f"  Question: \"{query}\"")

# Mock query embedding (same hash-based approach)
query_base = hash(query) % 100 / 100
query_embedding = [query_base + (j % 10) * 0.001 for j in range(1024)]
mag = sum(x*x for x in query_embedding) ** 0.5
query_embedding = [x / mag for x in query_embedding]

# Retrieve with cosine similarity
scores = []
for chunk_id, record in db.items():
    score = cosine_similarity(query_embedding, record["embedding"])
    scores.append((chunk_id, score, record))

# Sort by score descending
scores.sort(key=lambda x: x[1], reverse=True)

# Filter by min_score (0.75)
min_score = 0.75
results = [(cid, score, rec) for cid, score, rec in scores if score >= min_score]

print(f"\n  Retrieved chunks (min_score={min_score}):")
if results:
    for chunk_id, score, record in results[:3]:  # Top 3
        print(f"    [{score:.3f}] {record['heading_path']}")
        print(f"      {record['chunk_text'][:60]}...")
else:
    print(f"    (No chunks passed threshold)")

# Step 6: Response
print(f"\n[STEP 6] Generate Response")
if results:
    print(f"  Answer: \"A function is a reusable block of code...\"")
    print(f"  Sources: {[r[2]['heading_path'] for r in results[:2]]}")
else:
    print(f"  Fallback: \"I don't have that information in the provided documents.\"")

print(f"\n" + "=" * 60)
print(f"✓ Pipeline complete (no actual API calls or DB needed)")
print(f"=" * 60)
