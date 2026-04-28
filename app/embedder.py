import os
import voyageai


class VoyageEmbedder:
    """Voyage AI embeddings with input_type distinction for document/query."""

    def __init__(self, api_key: str = None, model: str = "voyage-3.5-lite"):
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY")
        if not self.api_key:
            raise ValueError("VOYAGE_API_KEY environment variable not set")
        self.model = model
        self.client = voyageai.Client(api_key=self.api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document chunks with input_type='document'."""
        response = self.client.embed(
            texts,
            model=self.model,
            input_type="document",
        )
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
    # Batch by 128 as per spec
    batch_size = 128
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = embedder.embed_documents(batch)
        all_embeddings.extend(embeddings)

    return all_embeddings
