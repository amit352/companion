CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS feature_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_id TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feature_embeddings_feature_id
    ON feature_embeddings(feature_id);

CREATE INDEX IF NOT EXISTS idx_feature_embeddings_vector
    ON feature_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
