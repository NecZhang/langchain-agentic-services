-- Initialize Agentic Service Database
-- This script creates all necessary tables for the agentic service

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255),
    email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(user_id, session_id)
);

-- Chat history table
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Documents table (metadata for uploaded files)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    original_filename VARCHAR(500) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    file_size BIGINT,
    file_type VARCHAR(100),
    mime_type VARCHAR(200),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'uploaded',
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(session_id, file_hash)
);

-- Document chunks table (for RAG processing)
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_hash VARCHAR(64) NOT NULL,
    chunk_size INTEGER,
    chunk_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- Processing caches table (for different processing modes)
CREATE TABLE IF NOT EXISTS processing_caches (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    document_hash VARCHAR(64) NOT NULL,
    processing_mode VARCHAR(100) NOT NULL,
    cache_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(session_id, document_hash, processing_mode)
);

-- Vector embeddings table (for semantic search)
CREATE TABLE IF NOT EXISTS vector_embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding_model VARCHAR(100) NOT NULL,
    embedding_vector REAL[] NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(chunk_id, embedding_model)
);

-- File storage table (for S3/MinIO file references)
CREATE TABLE IF NOT EXISTS file_storage (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    storage_backend VARCHAR(50) NOT NULL DEFAULT 'local',
    storage_path VARCHAR(1000),
    storage_url VARCHAR(1000),
    storage_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, storage_backend)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_session ON sessions(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_timestamp ON chat_history(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_documents_session_hash ON documents(session_id, file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_document_index ON document_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_caches_session_mode ON processing_caches(session_id, processing_mode);
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_model ON vector_embeddings(chunk_id, embedding_model);

-- Create full-text search index on chat content
CREATE INDEX IF NOT EXISTS idx_chat_content_search ON chat_history USING gin(to_tsvector('english', content));

-- Create JSONB indexes for metadata fields
CREATE INDEX IF NOT EXISTS idx_users_metadata ON users USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_sessions_metadata ON sessions USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING gin(metadata);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_caches_updated_at BEFORE UPDATE ON processing_caches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default user if not exists
INSERT INTO users (user_id, username) 
VALUES ('default_user', 'Default User')
ON CONFLICT (user_id) DO NOTHING;

-- Create default session for default user
INSERT INTO sessions (user_id, session_id)
SELECT 'default_user', 'default_session'
WHERE NOT EXISTS (
    SELECT 1 FROM sessions WHERE user_id = 'default_user' AND session_id = 'default_session'
);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agentic_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agentic_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO agentic_user;

