import os
import logging
import voyageai

logger = logging.getLogger(__name__)


class VoyageEmbedder:
    """Voyage AI embeddings with input_type distinction for document/query."""

    def __init__(self, api_key: str = None, model: str = "voyage-3.5-lite"):
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY") or os.getenv("DOCSQA_VOYAGE_API_KEY")
        if not self.api_key:
            raise ValueError("VOYAGE_API_KEY or DOCSQA_VOYAGE_API_KEY environment variable not set")
        self.model = model
        self.client = voyageai.Client(api_key=self.api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks with input_type='document'."""
        logger.debug(f"Embedding {len(texts)} documents with Voyage API")
        response = self.client.embed(
            texts,
            model=self.model,
            input_type="document",
        )
        logger.debug(f"Received {len(response.embeddings)} embeddings")
        return response.embeddings

    def embed_query(self, text: str) -> list[float]:
        """Embed query with input_type='query'."""
        response = self.client.embed(
            [text],
            model=self.model,
            input_type="query",
        )
        return response.embeddings[0]


_embedder = None


def get_embedder():
    """Get or create embedder singleton."""
    global _embedder
    if not _embedder:
        _embedder = VoyageEmbedder()
    return _embedder


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Batch embed document chunks."""
    embedder = get_embedder()
    batch_size = 128
    all_embeddings = []
    num_batches = (len(texts) + batch_size - 1) // batch_size

    logger.info(f"Embedding {len(texts)} texts in {num_batches} batches of {batch_size}")

    for i, start in enumerate(range(0, len(texts), batch_size)):
        end = min(start + batch_size, len(texts))
        batch = texts[start:end]
        logger.debug(f"Batch {i+1}/{num_batches}: embedding {len(batch)} texts")
        embeddings = embedder.embed_documents(batch)
        all_embeddings.extend(embeddings)

    logger.info(f"Completed embedding {len(all_embeddings)} texts")
    return all_embeddings
