-- Create chunks table with pgvector support
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    doc_name TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    heading_path TEXT,
    chunk_text TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create ivfflat index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create index on doc_name for filtering
CREATE INDEX IF NOT EXISTS chunks_doc_name_idx ON chunks(doc_name);
