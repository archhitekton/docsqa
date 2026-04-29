import logging
from app.models import Chunk

logger = logging.getLogger(__name__)


async def retrieve(question_embedding: list[float], top_k: int, pool) -> list[Chunk]:
    """Retrieve top-k chunks via cosine similarity search."""
    logger.debug(f"Retrieving top-{top_k} chunks")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, doc_name, chunk_index, chunk_text, embedding
            FROM chunks
            ORDER BY embedding <=> $1
            LIMIT $2
            """,
            question_embedding,
            top_k,
        )

    logger.info(f"Retrieved {len(rows)} chunks")

    chunks = [
        Chunk(
            id=row["id"],
            doc_name=row["doc_name"],
            chunk_index=row["chunk_index"],
            chunk_text=row["chunk_text"],
            embedding=row["embedding"],
        )
        for row in rows
    ]

    return chunks
