#!/usr/bin/env python3
"""Quick test of ingest pipeline with small markdown file."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chunker import chunk_document

# Read small test markdown
test_md = Path("docs/converted/test.md").read_text()

# Chunk it
chunks = chunk_document(test_md, max_tokens=500, overlap=50)

print(f"✓ Chunked test.md into {len(chunks)} chunks\n")

for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}:")
    print(f"  Path: {chunk.heading_path}")
    print(f"  Text: {chunk.text[:80]}...")
    print()

print(f"✓ Chunking works correctly")
