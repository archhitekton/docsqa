import logging
import asyncpg
from app.models import Chunk

logger = logging.getLogger(__name__)


async def retrieve(
    question_embedding: list[float],
    top_k: int,
    min_score: float,
    pool: asyncpg.Pool,
) -> list[Chunk]:
    """Retrieve top-k chunks by cosine similarity, filter by min_score.

    Cosine similarity: 1 - (embedding <=> question_embedding)
    where <=> is pgvector's distance operator.
    """
    logger.debug(f"Retrieving top {top_k} chunks (min_score={min_score})")

    async with pool.acquire() as conn:
        # Convert embedding to pgvector string format
        # pgvector expects: "[x,y,z,...]"
        embedding_str = "[" + ",".join(str(x) for x in question_embedding) + "]"

        # Query: cosine similarity with score filtering
        rows = await conn.fetch(
            """
            SELECT id, doc_name, chunk_index, heading_path, chunk_text, embedding,
                   1 - (embedding <=> $1::vector) AS score
            FROM chunks
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            embedding_str,
            top_k,
        )

    chunks = []
    for row in rows:
        score = row["score"]
        if score >= min_score:
            chunks.append(
                Chunk(
                    id=row["id"],
                    doc_name=row["doc_name"],
                    chunk_index=row["chunk_index"],
                    heading_path=row["heading_path"],
                    chunk_text=row["chunk_text"],
                    embedding=list(row["embedding"]),  # pgvector returns as list
                    score=score,
                )
            )

    logger.info(f"Retrieved {len(chunks)} chunks (from {top_k} candidates)")
    return chunks
