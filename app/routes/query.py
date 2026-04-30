import logging
from fastapi import APIRouter
import json

from app.models import QueryRequest, FallbackResponse, Source
from app.db import get_pool
from app.embedder import get_embedder
from app.retriever import retrieve
from app.llm import get_answer

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query")
async def query(request: QueryRequest):
    """Query the RAG system with JSON response.

    Returns:
    - If chunks pass min_score: {"answer": "...", "sources": [...]}
    - If no chunks pass: {"answer": "I don't have...", "sources": []}
    """
    logger.info(f"Query: {request.question[:60]}...")

    # Embed question
    logger.info(f"Embedding question: {request.question[:60]}...")
    embedder = get_embedder()
    question_embedding = embedder.embed_query(request.question)
    logger.info(f"Question embedded: {len(question_embedding)} dims")

    # Retrieve chunks with reranking
    # Reranker uses stricter scoring, so lower threshold
    reranker_min_score = 0.25
    logger.info(f"Retrieving chunks (top_k={request.top_k}, min_score={reranker_min_score} with reranking)...")
    pool = get_pool()
    chunks = await retrieve(
        question_embedding=question_embedding,
        top_k=request.top_k,
        min_score=reranker_min_score,
        pool=pool,
        question=request.question,
        use_reranker=True,
    )
    logger.info(f"Retrieved {len(chunks)} chunks from database")

    # Fallback: no chunks passed threshold
    if not chunks:
        logger.info("No chunks passed min_score threshold, returning fallback")
        fallback = FallbackResponse(
            answer="I don't have that information in the provided documents.",
            sources=[],
        )
        return fallback

    # Get answer from Claude
    logger.info(f"Getting answer from Claude with {len(chunks)} chunks")
    answer = await get_answer(request.question, chunks)

    # Build sources
    sources = [
        Source(
            filename=chunk.doc_name,
            heading_path=chunk.heading_path,
            chunk_id=chunk.id,
            excerpt=chunk.chunk_text[:200],  # First 200 chars as excerpt
        )
        for chunk in chunks
    ]

    logger.info(f"Returning answer with {len(sources)} sources")
    return {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
    }
