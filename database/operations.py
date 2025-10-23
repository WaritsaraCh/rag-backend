import time
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extensions import AsIs
import shortuuid
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json
import torch
import numpy as np
from config.settings import get_config

# ── Setup ─────────────────────────────────────────
config = get_config()

# Database configuration
DB_CONFIG = {
    'host': config.DB_HOST,
    'port': config.DB_PORT,
    'database': config.DB_NAME,
    'user': config.DB_USER,
    'password': config.DB_PASSWORD
}

# Connection pool
pool = SimpleConnectionPool(
    config.DB_POOL_MIN,
    config.DB_POOL_MAX,
    **DB_CONFIG
)

_embedder = SentenceTransformer("BAAI/bge-m3")
if torch.cuda.is_available():
    _embedder = _embedder.to("cuda")

SPLITTER = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)

# ── Utility ───────────────────────────────────────
def get_conn():
    return pool.getconn()

def release_conn(conn):
    pool.putconn(conn)

# Add db_query_one helper function
def db_query_one(query, params=None):
    """Execute a query and return one result"""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()
    finally:
        release_conn(conn)

def create_conversation_if_not_exists(session_id: str):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # First, try to find existing conversation
            cur.execute("""
                SELECT id FROM conversations WHERE session_id = %s LIMIT 1
            """, (session_id,))
            
            existing = cur.fetchone()
            if existing:
                return existing["id"]
            
            # If not found, create new conversation
            cur.execute("""
                INSERT INTO conversations (session_id)
                VALUES (%s)
                RETURNING id
            """, (session_id,))
            conn.commit()
            return cur.fetchone()["id"]
    finally:
        release_conn(conn)

def save_message(conversation_id, role, content, relevant_chunk_ids=None):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # ตรวจสอบว่า conversation มีอยู่จริง
            cur.execute("SELECT id FROM conversations WHERE id = %s", (conversation_id,))
            if not cur.fetchone():
                raise ValueError(f"Conversation with id {conversation_id} does not exist")

            # ✅ generate embedding
            embedding = _embedder.encode(content)
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()

            # แปลงเป็น string แบบ [0.123,0.456,...]
            vector_str = "[" + ",".join(f"{float(x):.6f}" for x in embedding) + "]"

            # ✅ Insert message + embedding vector with proper array handling
            if relevant_chunk_ids is not None:
                # Convert Python list to PostgreSQL array format
                chunk_ids_array = '{' + ','.join(map(str, relevant_chunk_ids)) + '}'
            else:
                chunk_ids_array = None
                
            cur.execute("""
                INSERT INTO messages (conversation_id, role, content, relevant_chunk_ids, embedding)
                VALUES (%s, %s, %s, %s, %s::vector)
                RETURNING id;
            """, (conversation_id, role, content, chunk_ids_array, vector_str))

            result = cur.fetchone()
            conn.commit()
            if result:
                # print(f"💾 Message saved: {result['id']}")
                return result["id"]
            else:
                print("⚠️ Message insert failed")
                return None

    except Exception as e:
        conn.rollback()
        print(f"❌ Error saving message: {e}")
        raise
    finally:
        release_conn(conn)

def add_document_with_chunks(title, content, source_type, source_url, metadata):
    """Add a document and its chunks to the database with optimized batch processing"""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        
        # Insert document
        cursor.execute("""
            INSERT INTO documents (title, source_type, source_url, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (title, source_type, source_url, json.dumps(metadata)))
        
        document_id = cursor.fetchone()[0]
        
        # Split content into chunks
        chunks = SPLITTER.split_text(content)
        
        # Generate embeddings in optimized batches with caching
        print(f"🔄 Generating embeddings for {len(chunks)} chunks...")
        embeddings = _embedder.encode(chunks)
        
        # Prepare batch insert data
        chunk_data = []
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            # Convert to list if it's a numpy array
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
                
            # Convert embedding to PostgreSQL vector format
            vector_str = "[" + ",".join(f"{float(x):.6f}" for x in embedding) + "]"
                
            chunk_data.append((
                document_id,
                chunk_text,
                i,  # chunk_index
                vector_str,  # embedding as vector string
                json.dumps(metadata)  
            ))
        
        # Batch insert chunks
        cursor.executemany("""
            INSERT INTO document_chunks (document_id, chunk_text, chunk_index, embedding, metadata)
            VALUES (%s, %s, %s, %s::vector, %s)
        """, chunk_data)
        
        conn.commit()
        print(f"✅ Document '{title}' added with {len(chunks)} chunks")
        return document_id
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error adding document: {e}")
        raise
    finally:
        release_conn(conn)

def retrieve_docs(query_text=None, query_embedding=None, limit=5, similarity_threshold=0.5):
    """Retrieve similar document chunks using pgvector search function"""
    if query_embedding is None and query_text:
       
        query_embedding = _embedder.encode(query_text)
        # print(f"Generated embedding: {query_embedding}")

    # แปลง numpy array → Python list
    if hasattr(query_embedding, 'tolist'):
        query_embedding = query_embedding.tolist()

    # แปลงเป็น string ที่ PostgreSQL เข้าใจ เช่น [0.123,0.456,...]
    vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    conn = get_conn()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT * FROM search_similar_chunks(%s::vector, %s, %s);
        """, (vector_str, limit, similarity_threshold))

        results = cursor.fetchall()
        return results

    except Exception as e:
        print(f"❌ Error retrieving documents: {e}")
        raise
    finally:
        release_conn(conn)

def get_recent_messages(session_id, limit=3):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = '''
                SELECT role, content, relevant_chunk_ids FROM messages
                WHERE conversation_id = %s
                ORDER BY id DESC
                LIMIT %s
            '''
            cur.execute(sql, (session_id, limit))
            result = cur.fetchall()

            # Reverse the result to have the oldest message first
            result.reverse()
            return result
    finally:
        release_conn(conn)