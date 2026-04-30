#!/usr/bin/env python3
"""Test full ingest pipeline (chunking + mock embedding)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chunker import chunk_document

# Read small test markdown
test_md = Path("docs/converted/test.md").read_text()

# Step 1: Chunking
chunks = chunk_document(test_md, max_tokens=500, overlap=50)
print(f"✓ Step 1: Chunked into {len(chunks)} chunks")

# Step 2: Mock embeddings (simulating Voyage API call)
# In production, this would call voyageai.Client().embed()
mock_embeddings = [
    [0.1 + (i * 0.01)] * 1024  # Simple mock: [0.1, 0.11, 0.12, ...]
    for i in range(len(chunks))
]
print(f"✓ Step 2: Generated {len(mock_embeddings)} mock embeddings (1024-dim)")

# Step 3: Prepare database inserts
records = []
for i, (chunk, embedding) in enumerate(zip(chunks, mock_embeddings)):
    record = {
        "doc_name": "test.md",
        "chunk_index": i,
        "heading_path": chunk.heading_path,
        "chunk_text": chunk.text,
        "embedding": embedding,
    }
    records.append(record)

print(f"✓ Step 3: Prepared {len(records)} records for database insertion")

# Step 4: Display sample record
sample = records[0]
print(f"\nSample record:")
print(f"  doc_name: {sample['doc_name']}")
print(f"  chunk_index: {sample['chunk_index']}")
print(f"  heading_path: {sample['heading_path']}")
print(f"  chunk_text: {sample['chunk_text'][:60]}...")
print(f"  embedding: [{sample['embedding'][0]}, {sample['embedding'][1]}, ...] (len={len(sample['embedding'])})")

print(f"\n✓ Full ingest pipeline validated (ready for DB storage)")
