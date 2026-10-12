CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE legal.chunks ADD COLUMN embedding vector(1024), ADD COLUMN embedding_revision text;
CREATE INDEX chunks_vector ON legal.chunks USING hnsw(embedding vector_cosine_ops);
