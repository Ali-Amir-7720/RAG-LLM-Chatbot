-- ============================================================
-- CLEANUP SCRIPT - Drop complex tables if they exist
-- ============================================================
-- Run this to clean up old tables from the previous schema

-- Drop tables that depend on the document_status enum first
DROP TABLE IF EXISTS chunk_embeddings CASCADE;
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

-- Now drop the rest
DROP TABLE IF EXISTS message_citations CASCADE;
DROP TABLE IF EXISTS attachments CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;

-- Drop old triggers and functions
DROP TRIGGER IF EXISTS update_users_updated_at ON users CASCADE;
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations CASCADE;
DROP TRIGGER IF EXISTS update_user_sessions_updated_at ON user_sessions CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;

-- Drop old enums (now safe after dropping dependent tables)
DROP TYPE IF EXISTS document_status CASCADE;

COMMIT;
