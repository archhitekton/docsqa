import asyncio
import os
import sys
import logging
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

import pdfplumber

from app.db import init_pool, close_pool, get_pool
from app.chunker import chunk_text
from app.embedder import embed_batch

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)


def extract_pdf_text(file_path: Path) -> str:
    """Extract text from PDF using pdfplumber."""
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            logging.debug(f"PDF has {len(pdf.pages)} pages")
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                    logging.debug(f"Extracted page {i+1}: {len(page_text)} chars")
    except Exception as e:
        logging.error(f"Failed to parse {file_path.name}: {e}")
        return ""
    return "\n\n".join(text_parts)


async def ingest_documents(dry_run=False):
    """Ingest documents from ./docs/ directory."""
    logging.info("Initializing database pool...")
    await init_pool()
    logging.info("Pool initialized")

    try:
        docs_dir = Path("docs")
        if not docs_dir.exists():
            logging.error("docs/ directory not found")
            return

        if dry_run:
            logging.info("DB connected (dry-run mode)")
            return

        pool = get_pool()
        files = list(docs_dir.glob("*.md")) + list(docs_dir.glob("*.pdf"))
        logging.info(f"Found {len(files)} files to ingest")

        total_chunks = 0
        for file_path in files:
            logging.info(f"Processing {file_path.name}...")

            if file_path.suffix == ".md":
                text = file_path.read_text()
                logging.debug(f"Loaded .md file: {len(text)} chars")
            elif file_path.suffix == ".pdf":
                text = extract_pdf_text(file_path)
                logging.debug(f"Extracted PDF: {len(text)} chars")
            else:
                continue

            if not text.strip():
                logging.warning(f"Skipped {file_path.name} (empty)")
                continue

            logging.info(f"Chunking {file_path.name}...")
            chunks = chunk_text(text, max_tokens=500, overlap=50)
            logging.info(f"Generated {len(chunks)} chunks")

            logging.info(f"Embedding {len(chunks)} chunks...")
            embeddings = await embed_batch(chunks)
            logging.info(f"Embedded {len(embeddings)} chunks")

            logging.info(f"Inserting into database...")
            async with pool.acquire() as conn:
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    # Convert embedding list to string format for pgvector
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    await conn.execute(
                        """
                        INSERT INTO chunks (doc_name, chunk_index, chunk_text, embedding)
                        VALUES ($1, $2, $3, $4::vector)
                        """,
                        file_path.name,
                        i,
                        chunk,
                        embedding_str,
                    )

            total_chunks += len(chunks)
            logging.info(f"✓ Ingested {len(chunks)} chunks from {file_path.name}")

        logging.info(f"✓ Ingestion complete. Total chunks: {total_chunks}")

    finally:
        logging.info("Closing database pool...")
        await close_pool()
        logging.info("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Test DB connection only")
    args = parser.parse_args()

    asyncio.run(ingest_documents(dry_run=args.dry_run))
