#!/usr/bin/env python3
"""Ingest documents: convert, chunk, embed, and store in Supabase."""

import asyncio
import os
import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from markitdown import MarkItDown
from app.db import init_pool, close_pool, get_pool
from app.chunker import chunk_document
from app.embedder import embed_batch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def convert_to_markdown(file_path: Path) -> str:
    """Convert PDF or read Markdown file to markdown string.

    PDFs: Convert with markitdown to preserve heading hierarchy, code blocks, lists.
    Markdown: Read directly.
    """
    if file_path.suffix == ".pdf":
        logger.info(f"Converting PDF: {file_path.name}")
        try:
            md = MarkItDown()
            result = md.convert(str(file_path))
            return result.text_content
        except Exception as e:
            logger.error(f"Failed to parse {file_path.name}: {e}")
            return ""
    elif file_path.suffix == ".md":
        logger.info(f"Reading Markdown: {file_path.name}")
        return file_path.read_text()
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")


def save_intermediate_markdown(filename: str, markdown: str):
    """Save intermediate markdown to docs/converted/ for inspection."""
    converted_dir = Path("docs/converted")
    converted_dir.mkdir(exist_ok=True)

    output_path = converted_dir / f"{Path(filename).stem}.md"
    output_path.write_text(markdown)
    logger.debug(f"Saved intermediate markdown: {output_path}")


async def ingest_documents(dry_run=False):
    """Ingest documents from ./docs/ directory."""
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
        docs_dir = Path("docs")
        if not docs_dir.exists():
            logger.error("docs/ directory not found")
            return

        pool = get_pool()

        # Find all PDF and Markdown files
        files = sorted(list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.pdf")))
        files = [f for f in files if f.name not in ["spec.md", "sample-adr.md"]]  # Skip docs

        logger.info(f"Found {len(files)} files to ingest")

        total_chunks = 0

        for file_path in files:
            logger.info(f"Processing {file_path.name}...")

            # Convert to markdown
            markdown = convert_to_markdown(file_path)
            if not markdown.strip():
                logger.warning(f"Skipped {file_path.name} (empty)")
                continue

            logger.debug(f"Converted/read: {len(markdown)} chars")

            # Save intermediate markdown for inspection
            save_intermediate_markdown(file_path.name, markdown)

            # Chunk document
            logger.info(f"Chunking {file_path.name}...")
            chunks = chunk_document(markdown, max_tokens=500, overlap=50)
            logger.info(f"Generated {len(chunks)} chunks")

            if not chunks:
                logger.warning(f"No chunks generated from {file_path.name}")
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
                        file_path.name,
                        i,
                        chunk.heading_path,
                        chunk.text,
                        embedding,  # asyncpg can directly encode list as vector
                    )

            total_chunks += len(chunks)
            logger.info(f"✓ Ingested {len(chunks)} chunks from {file_path.name}")

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
