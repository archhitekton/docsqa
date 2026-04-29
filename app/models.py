from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)


class Chunk(BaseModel):
    id: int
    doc_name: str
    chunk_index: int
    chunk_text: str
    embedding: list[float]


class Source(BaseModel):
    filename: str
    chunk_id: int
    excerpt: str
