-- 阶段6：pgvector 初始化脚本（默认表名与配置保持一致）
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS event_evidence_vectors (
    doc_id TEXT PRIMARY KEY,
    document TEXT NOT NULL,
    embedding vector NOT NULL,
    metadata JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_evidence_vectors_embedding_ivfflat
    ON event_evidence_vectors
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_event_evidence_vectors_updated_at
    ON event_evidence_vectors (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_event_evidence_vectors_metadata_gin
    ON event_evidence_vectors USING gin (metadata);
