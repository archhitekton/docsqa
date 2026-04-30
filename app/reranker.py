import os
import logging
import voyageai

logger = logging.getLogger(__name__)


class VoyageReranker:
    """Voyage AI reranker for cross-encoder relevance scoring."""

    def __init__(self, api_key: str = None, model: str = "rerank-2.5-lite"):
        self.api_key = api_key or os.getenv("VOYAGE_API_KEY") or os.getenv("DOCSQA_VOYAGE_API_KEY")
        if not self.api_key:
            raise ValueError("VOYAGE_API_KEY or DOCSQA_VOYAGE_API_KEY environment variable not set")
        self.model = model
        self.client = voyageai.Client(api_key=self.api_key)

    def rerank(self, query: str, documents: list[str], top_k: int = None) -> list[dict]:
        """Rerank documents by relevance to query.

        Args:
            query: User question/query
            documents: List of document chunks to rerank
            top_k: Return top-k results (None = all)

        Returns:
            List of dicts with 'index', 'relevance_score', 'document'
        """
        if not documents:
            return []

        logger.debug(f"Reranking {len(documents)} documents for query: {query[:60]}...")

        response = self.client.rerank(
            model=self.model,
            query=query,
            documents=documents,
            top_k=top_k,
        )

        logger.debug(f"Reranked: got {len(response.results)} results")

        # Convert to list of dicts for easier handling
        return [
            {
                "index": result.index,
                "relevance_score": result.relevance_score,
                "document": documents[result.index],
            }
            for result in response.results
        ]


_reranker = None


def get_reranker():
    """Get or create reranker singleton."""
    global _reranker
    if not _reranker:
        _reranker = VoyageReranker()
    return _reranker
