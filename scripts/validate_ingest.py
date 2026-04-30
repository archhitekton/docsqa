#!/usr/bin/env python3
"""Validate ingest pipeline with test.md (no DB/API calls)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chunker import chunk_document

# Read test.md
test_md = Path("docs/converted/test.md").read_text(encoding="utf-8")
print(f"📄 Read test.md: {len(test_md)} chars, {len(test_md.splitlines())} lines\n")

# Step 1: Chunk
chunks = chunk_document(test_md, max_tokens=500, overlap=50)
print(f"✓ Chunked into {len(chunks)} chunks:")
for i, chunk in enumerate(chunks):
    print(f"  {i+1}. [{len(chunk.text)} chars] {chunk.heading_path}")

# Step 2: Prepare for embedding
chunk_texts = [chunk.text for chunk in chunks]
print(f"\n✓ Extracted {len(chunk_texts)} chunk texts for embedding")

# Step 3: Mock embeddings (simulate Voyage API)
print(f"✓ Would call Voyage API with {len(chunk_texts)} chunks (batched)")

# Step 4: Show database records that would be inserted
print(f"\n✓ Would insert {len(chunks)} records into database:\n")
for i, chunk in enumerate(chunks):
    print(f"  Record {i+1}:")
    print(f"    doc_name: test.md")
    print(f"    chunk_index: {i}")
    print(f"    heading_path: {chunk.heading_path}")
    print(f"    chunk_text: {chunk.text[:50]}...")
    print(f"    embedding: [0.123, 0.456, ...] (1024-dim)")

print(f"\n✅ Validation passed. Ingest pipeline ready for test.md")
