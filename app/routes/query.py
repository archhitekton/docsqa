import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json

from app.models import QueryRequest, Source
from app.embedder import get_embedder
from app.retriever import retrieve
from app.llm import stream_answer
from app.db import get_pool

logger = logging.getLogger(__name__)

router = APIRouter()


async def query_generator(question: str, top_k: int):
    """Generator for streaming query response with sources."""
    try:
        # Embed question
        logger.info(f"Query: {question}")
        embedder = get_embedder()
        question_embedding = embedder.embed_query(question)
        logger.debug(f"Question embedded: {len(question_embedding)} dims")

        # Retrieve chunks
        pool = get_pool()
        chunks = await retrieve(question_embedding, top_k, pool)

        if not chunks:
            yield 'data: {"error": "No relevant documents found"}\n\n'
            return

        # Stream answer
        logger.info(f"Streaming answer with {len(chunks)} context chunks")
        async for token in stream_answer(question, chunks):
            # Escape newlines in tokens for SSE format
            token_escaped = token.replace("\n", "\\n")
            yield f"data: {token_escaped}\n\n"

        # Send done marker
        yield "data: [DONE]\n\n"

        # Send sources as trailing JSON event
        sources = [
            Source(
                filename=chunk.doc_name,
                chunk_id=chunk.id,
                excerpt=chunk.chunk_text[:200],
            )
            for chunk in chunks
        ]
        sources_json = json.dumps({"sources": [s.model_dump() for s in sources]})
        yield f"data: {sources_json}\n\n"

    except Exception as e:
        logger.error(f"Error in query: {e}", exc_info=True)
        yield f'data: {{"error": "{str(e)}"}}\n\n'


@router.post("/query")
async def query(request: QueryRequest):
    """POST /query endpoint with streaming response."""
    return StreamingResponse(
        query_generator(request.question, request.top_k),
        media_type="text/event-stream",
    )
