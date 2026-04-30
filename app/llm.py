import logging
from typing import AsyncGenerator
import anthropic
from app.models import Chunk

logger = logging.getLogger(__name__)


def build_prompt(question: str, chunks: list[Chunk]) -> tuple[str, str]:
    """Build system and user prompts with retrieved context and source labels."""
    # Format context with source labels: [filename#chunk_id]
    context_parts = []
    for chunk in chunks:
        source_label = f"[{chunk.doc_name}#{chunk.chunk_index}]"
        if chunk.heading_path:
            source_label += f" ({chunk.heading_path})"
        context_parts.append(f"{source_label}\n{chunk.chunk_text}")

    context = "\n\n".join(context_parts)

    system_prompt = """You are a helpful assistant that answers questions based on provided documents.
Answer the question using only the provided context. Be concise and direct.
Always cite your sources using the format [filename#chunk_id] when referencing specific information."""

    user_prompt = f"""Question: {question}

Context:
{context}

Answer the question based on the provided context. If the context is insufficient to answer, say so."""

    return system_prompt, user_prompt


async def stream_answer(
    question: str, chunks: list[Chunk]
) -> AsyncGenerator[str, None]:
    """Stream answer tokens from Claude."""
    system_prompt, user_prompt = build_prompt(question, chunks)

    client = anthropic.Anthropic()
    logger.info(f"Calling Claude with {len(chunks)} context chunks")

    with client.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            logger.debug(f"Streamed token: {len(text)} chars")
            yield text
