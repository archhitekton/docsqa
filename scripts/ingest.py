import asyncio
import os
import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_pool, close_pool, get_pool
from app.chunker import chunk_text
from app.embedder import embed_batch


async def ingest_documents(dry_run=False):
    """Ingest documents from ./docs/ directory."""
    await init_pool()

    try:
        docs_dir = Path("docs")
        if not docs_dir.exists():
            print("❌ docs/ directory not found")
            return

        if dry_run:
            print("✓ DB connected")
            return

        pool = get_pool()
        files = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.pdf"))

        for file_path in files:
            if file_path.suffix == ".md":
                text = file_path.read_text()
            elif file_path.suffix == ".pdf":
                # PDF parsing via pdfplumber (to be implemented)
                text = ""
            else:
                continue

            chunks = chunk_text(text, max_tokens=500, overlap=50)
            embeddings = await embed_batch(chunks)

            async with pool.acquire() as conn:
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    await conn.execute(
                        """
                        INSERT INTO chunks (doc_name, chunk_index, chunk_text, embedding)
                        VALUES ($1, $2, $3, $4)
                        """,
                        file_path.name,
                        i,
                        chunk,
                        embedding,
                    )

            print(f"Ingested {len(chunks)} chunks from {file_path.name}")

    finally:
        await close_pool()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Test DB connection only")
    args = parser.parse_args()

    asyncio.run(ingest_documents(dry_run=args.dry_run))
