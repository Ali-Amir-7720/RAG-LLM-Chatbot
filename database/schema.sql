-- ============================================================
-- EXTENSIONS
-- ============================================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- ENUMS
-- ============================================================
CREATE TYPE document_status AS ENUM ('uploading', 'processing', 'ready', 'failed');
CREATE TYPE message_role AS ENUM ('system', 'user', 'assistant');

-- ============================================================
-- AUTOMATED TIMESTAMP TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================
-- 1. USERS
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    profile_picture TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_users_email_lower ON users (LOWER(email));
CREATE UNIQUE INDEX idx_users_username_lower ON users (LOWER(username));

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 2. USER SESSIONS
-- ============================================================
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL,
    device TEXT,
    ip_address INET,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE UNIQUE INDEX idx_sessions_token ON user_sessions(refresh_token);

CREATE TRIGGER update_user_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 3. EMBEDDING MODELS
-- ============================================================
-- Registry of models available to the system. Note: chunk_embeddings.embedding
-- is currently pinned to VECTOR(1536) — registering a model with a different
-- dimension will fail on insert, not at registration time. See table 11 below.
CREATE TABLE embedding_models (
    id SMALLSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,     -- e.g. 'text-embedding-3-large'
    dimension SMALLINT NOT NULL,           -- e.g. 1536
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 4. CONVERSATIONS
-- ============================================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New conversation',
    model_name VARCHAR(100) NOT NULL,
    system_prompt TEXT,
    generation_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_archived BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_conversations_user ON conversations(user_id);

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 5. MESSAGES
-- ============================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    parent_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    role message_role NOT NULL,
    content TEXT NOT NULL,
    model_name VARCHAR(100),
    token_count INTEGER,
    generation_time REAL,
    is_helpful BOOLEAN,
    feedback_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_conv_created ON messages(conversation_id, created_at);

-- ============================================================
-- 6. DOCUMENTS
-- ============================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    storage_path TEXT NOT NULL,
    content_hash CHAR(64) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    status document_status NOT NULL DEFAULT 'uploading',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_documents_hash ON documents(content_hash);

-- ============================================================
-- 7. USER DOCUMENTS
-- ============================================================
CREATE TABLE user_documents (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, document_id)
);
CREATE INDEX idx_user_documents_doc ON user_documents(document_id);

-- ============================================================
-- 8. CONVERSATION DOCUMENTS
-- ============================================================
CREATE TABLE conversation_documents (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (conversation_id, document_id)
);
CREATE INDEX idx_convdocs_document ON conversation_documents(document_id);

-- ============================================================
-- 9. ATTACHMENTS
-- ============================================================
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_path TEXT NOT NULL,
    thumbnail_path TEXT,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_attachments_message ON attachments(message_id);

-- ============================================================
-- 10. DOCUMENT CHUNKS (text, independent of embedding model)
-- ============================================================
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    page_number INTEGER,
    chunk_text TEXT NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_number)
);
CREATE INDEX idx_chunks_document ON document_chunks(document_id);

-- ============================================================
-- 11. CHUNK EMBEDDINGS
-- ============================================================
-- Pinned to VECTOR(1536). If you register a model with a different dimension
-- in embedding_models, inserts for that model will fail here — either keep
-- the system single-dimension, or split this table per dimension when you
-- actually need a second model.
CREATE TABLE chunk_embeddings (
    chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding_model_id SMALLINT NOT NULL REFERENCES embedding_models(id),
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (chunk_id, embedding_model_id)
);

CREATE INDEX idx_chunk_embeddings_hnsw
    ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);

-- Supports filtering by model before/alongside the ANN search
CREATE INDEX idx_chunk_embeddings_model ON chunk_embeddings(embedding_model_id);

-- ============================================================
-- 12. MESSAGE CITATIONS
-- ============================================================
-- embedding_model_id records which model's embedding actually produced the
-- similarity_score/rank for this citation. Composite FK ties it back to the
-- specific (chunk_id, embedding_model_id) row in chunk_embeddings, so a
-- citation can never reference a model/chunk pair that was never embedded.
CREATE TABLE message_citations (
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding_model_id SMALLINT NOT NULL REFERENCES embedding_models(id),
    similarity_score REAL,
    rank SMALLINT,
    PRIMARY KEY (message_id, chunk_id, embedding_model_id),
    FOREIGN KEY (chunk_id, embedding_model_id)
        REFERENCES chunk_embeddings(chunk_id, embedding_model_id)
        ON DELETE CASCADE
);
CREATE INDEX idx_citations_chunk ON message_citations(chunk_id);

-- ============================================================
-- Example similarity search
-- ============================================================
-- SELECT dc.chunk_text, dc.page_number, ce.chunk_id
-- FROM chunk_embeddings ce
-- JOIN document_chunks dc ON dc.id = ce.chunk_id
-- JOIN conversation_documents cd ON cd.document_id = dc.document_id
-- WHERE cd.conversation_id = $1
--   AND ce.embedding_model_id = $2
-- ORDER BY ce.embedding <=> $3
-- LIMIT 5;