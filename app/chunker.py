import tiktoken
import logging

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> list[str]:
    """
    Chunk text into overlapping segments based on token count.

    Args:
        text: Text to chunk
        max_tokens: Max tokens per chunk (~500)
        overlap: Token overlap between chunks (~50)

    Returns:
        List of chunk strings
    """
    logger.debug(f"Encoding text: {len(text)} chars")
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    logger.debug(f"Tokenized: {len(tokens)} tokens")

    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text.strip())

        # Move start by (max_tokens - overlap) for next chunk
        start = end - overlap
        if start >= len(tokens):
            break

    result = [c for c in chunks if c]
    logger.info(f"Created {len(result)} chunks from {len(tokens)} tokens")
    return result
