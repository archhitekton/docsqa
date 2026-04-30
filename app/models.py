from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request body for /query endpoint."""
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)


class Chunk(BaseModel):
    """Chunk retrieved from database."""
    id: int
    doc_name: str
    chunk_index: int
    heading_path: str | None
    chunk_text: str
    embedding: list[float]
    score: float | None = None


class Source(BaseModel):
    """Source citation in answer."""
    filename: str
    heading_path: str | None
    chunk_id: int
    excerpt: str


class FallbackResponse(BaseModel):
    """Response when no chunks pass min_score threshold."""
    answer: str
    sources: list[Source]
