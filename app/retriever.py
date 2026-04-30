import logging
import asyncpg
from app.models import Chunk
from app.reranker import get_reranker

logger = logging.getLogger(__name__)


async def retrieve(
    question_embedding: list[float],
    top_k: int,
    min_score: float,
    pool: asyncpg.Pool,
    question: str = None,
    use_reranker: bool = False,
) -> list[Chunk]:
    """Retrieve top-k chunks by cosine similarity, optionally rerank.

    If use_reranker=True, retrieves 2x candidates and reranks with Voyage reranker.
    Otherwise uses cosine similarity: 1 - (embedding <=> question_embedding)
    """
    logger.debug(f"Retrieving top {top_k} chunks (min_score={min_score}, reranker={use_reranker})")

    async with pool.acquire() as conn:
        # Convert embedding to pgvector string format
        # pgvector expects: "[x,y,z,...]"
        embedding_str = "[" + ",".join(str(x) for x in question_embedding) + "]"

        # If reranking enabled, retrieve 2x candidates for reranking
        candidate_limit = (top_k * 2) if use_reranker else top_k

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
            candidate_limit,
        )

    # Build candidate chunks with similarity scores
    candidates = []
    for row in rows:
        # Parse pgvector string representation to list of floats
        emb_str = row["embedding"]
        if isinstance(emb_str, str):
            # Parse "[x,y,z,...]" format
            emb_list = [float(x) for x in emb_str.strip("[]").split(",")]
        else:
            emb_list = list(emb_str)

        candidates.append(
            Chunk(
                id=row["id"],
                doc_name=row["doc_name"],
                chunk_index=row["chunk_index"],
                heading_path=row["heading_path"],
                chunk_text=row["chunk_text"],
                embedding=emb_list,
                score=row["score"],
            )
        )

    # Rerank if enabled and we have a question
    if use_reranker and question and candidates:
        logger.info(f"Reranking {len(candidates)} candidates...")
        reranker = get_reranker()

        # Prepare documents for reranking
        doc_texts = [c.chunk_text for c in candidates]

        # Call reranker
        reranked = reranker.rerank(question, doc_texts, top_k=top_k)

        # Build reranked chunks with reranker scores
        reranked_chunks = []
        for result in reranked:
            candidate = candidates[result["index"]]
            # Use reranker score (typically stricter than cosine similarity)
            reranked_chunks.append(
                Chunk(
                    id=candidate.id,
                    doc_name=candidate.doc_name,
                    chunk_index=candidate.chunk_index,
                    heading_path=candidate.heading_path,
                    chunk_text=candidate.chunk_text,
                    embedding=candidate.embedding,
                    score=result["relevance_score"],
                )
            )

        logger.info(f"Reranked results: {len(reranked_chunks)} chunks")
        candidates = reranked_chunks

    # Filter by min_score
    chunks = [c for c in candidates if c.score >= min_score]

    logger.info(f"Retrieved {len(chunks)} chunks (from {len(candidates)} candidates)")
    return chunks
