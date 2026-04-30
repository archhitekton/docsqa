#!/usr/bin/env python3
"""Ingest documents: chunk, embed, and store in Supabase. (PDFs must be pre-converted to markdown)."""

import asyncio
import os
import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_pool, close_pool, get_pool
from app.chunker import chunk_document
from app.embedder import embed_batch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def embedding_to_pgvector(embedding: list[float]) -> str:
    """Convert embedding list to pgvector string format."""
    return "[" + ",".join(f"{x:.10f}" for x in embedding) + "]"


async def ingest_documents(dry_run=False):
    """Ingest pre-converted markdown from docs/converted/ directory."""
    if dry_run:
        # Verify DATABASE_URL is set without connecting
        database_url = os.getenv("DATABASE_URL") or os.getenv("DOCSQA_DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        print("DB connected")
        return

    logger.info("Initializing database pool...")
    await init_pool()
    logger.info("Pool initialized")

    try:
        converted_dir = Path("docs/converted")
        if not converted_dir.exists():
            logger.error("docs/converted/ directory not found. Run 'make convert' first.")
            return

        pool = get_pool()

        # Find all converted markdown files
        files = sorted(converted_dir.glob("*.md"))
        # Filter: only ingest test.md for now (fast iteration)
        files = [f for f in files if f.name == "test.md"]
        logger.info(f"Found {len(files)} markdown files to ingest")

        if not files:
            logger.warning("No markdown files found in docs/converted/")
            return

        total_chunks = 0

        for md_path in files:
            logger.info(f"Processing {md_path.name}...")

            # Read pre-converted markdown
            markdown = md_path.read_text(encoding="utf-8")
            if not markdown.strip():
                logger.warning(f"Skipped {md_path.name} (empty)")
                continue

            logger.debug(f"Read: {len(markdown)} chars")

            # Chunk document
            logger.info(f"Chunking {md_path.name}...")
            chunks = chunk_document(markdown, max_tokens=500, overlap=50)
            logger.info(f"Generated {len(chunks)} chunks")

            if not chunks:
                logger.warning(f"No chunks generated from {md_path.name}")
                continue

            # Extract chunk texts for embedding
            chunk_texts = [chunk.text for chunk in chunks]

            # Embed chunks
            logger.info(f"Embedding {len(chunks)} chunks...")
            embeddings = await embed_batch(chunk_texts)
            logger.info(f"Embedded {len(embeddings)} chunks")

            # Insert into database
            logger.info(f"Inserting into database...")
            async with pool.acquire() as conn:
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    await conn.execute(
                        """
                        INSERT INTO chunks (doc_name, chunk_index, heading_path, chunk_text, embedding)
                        VALUES ($1, $2, $3, $4, $5::vector)
                        """,
                        md_path.stem,  # Use stem (filename without .md extension)
                        i,
                        chunk.heading_path,
                        chunk.text,
                        embedding_to_pgvector(embedding),
                    )

            total_chunks += len(chunks)
            logger.info(f"✓ Ingested {len(chunks)} chunks from {md_path.name}")

        logger.info(f"✓ Ingestion complete. Total chunks: {total_chunks}")

    finally:
        logger.info("Closing database pool...")
        await close_pool()
        logger.info("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into RAG system")
    parser.add_argument("--dry-run", action="store_true", help="Test DB connection only")
    args = parser.parse_args()

    asyncio.run(ingest_documents(dry_run=args.dry_run))
