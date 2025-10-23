-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Documents table - เก็บเอกสารต้นฉบับ
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(50), -- 'pdf', 'web', 'manual', etc.
    source_url TEXT,
    metadata JSONB, -- flexible metadata storage
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Document chunks - เก็บข้อความที่แบ่งเป็นชิ้นเล็กๆ
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL, -- ลำดับของ chunk ในเอกสาร
    embedding vector(1024), -- สำหรับ OpenAI embeddings (1024 dimensions)
    metadata JSONB, -- เก็บข้อมูลเพิ่มเติม เช่น page_number, section_title
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image_paths TEXT, --เก็บข้อมูล paths ของรูปภาพ
    CONSTRAINT unique_chunk_per_doc UNIQUE(document_id, chunk_index)
);

-- 3. Conversations - เก็บประวัติการสนทนา
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- 4. Messages - เก็บข้อความในแต่ละ conversation
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    relevant_chunk_ids INTEGER[], -- เก็บ chunk ids ที่ใช้ตอบคำถามนี้
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector(1024) 
);



-- Vector similarity search index (สำคัญมาก!)
CREATE INDEX idx_chunk_embedding 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 8, ef_construction = 32);

-- Regular indexes
CREATE INDEX idx_chunk_document ON document_chunks(document_id);
CREATE INDEX idx_message_conversation ON messages(conversation_id);
CREATE INDEX idx_conversation_session ON conversations(session_id);
CREATE INDEX idx_documents_created ON documents(created_at DESC);

-- JSONB indexes for metadata queries
CREATE INDEX idx_doc_metadata ON documents USING GIN (metadata);
CREATE INDEX idx_chunk_metadata ON document_chunks USING GIN (metadata);



CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(1024),
    match_count INTEGER DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.5,
    doc_filter INTEGER DEFAULT NULL
)
RETURNS TABLE (
    chunk_id INTEGER,
    document_id INTEGER,
    chunk_text TEXT,
    image_paths TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- ปรับ parameter สำหรับ HNSW
    PERFORM set_config('hnsw.ef_search', '100', false);

    RETURN QUERY
    WITH candidates AS (
        SELECT
            id AS chunk_id,
            dc.document_id,
            chunk_text,
            image_paths,
            (1 - (embedding <=> query_embedding)) AS similarity
        FROM document_chunks dc
        WHERE (doc_filter IS NULL OR dc.document_id = doc_filter)
        ORDER BY embedding <=> query_embedding
        LIMIT match_count * 2
    )
    SELECT c.chunk_id, c.document_id, c.chunk_text, c.image_paths, c.similarity
    FROM candidates c
    WHERE c.similarity >= similarity_threshold
    ORDER BY c.similarity DESC
    LIMIT match_count;
END;
$$;
