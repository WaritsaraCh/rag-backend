import os
import time
from flask import Blueprint, request, jsonify
from utils.document_loaders import load_file_content
from utils.llm import generate_answer
from database.operations import (
    get_conn,
    release_conn,
    save_message,
    create_conversation_if_not_exists,
    add_document_with_chunks,
    retrieve_docs,
    get_recent_messages
)
from psycopg2.extras import RealDictCursor
from auth.user_manager import UserManager

# Create blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index():
    """Health check endpoint"""
    return jsonify({"message": "RAG Project API is running!", "status": "healthy"})

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login endpoint for user authentication"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Verify user credentials
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, email, full_name, is_admin, password_hash
                FROM users
                WHERE email = %s AND is_active = TRUE
                LIMIT 1
                """,
                (email,)
            )
            user = cur.fetchone()
            
            if not user or not UserManager.verify_password(password, user['password_hash']):
                return jsonify({"error": "Invalid credentials"}), 401
                
            return jsonify({
                "message": "Login successful",
                "user_id": user['id'],
                "email": user['email'],
                "full_name": user.get('full_name'),
                "is_admin": user.get('is_admin', False)
            })
    finally:
        release_conn(conn)


@api_bp.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint for conversational AI"""
    data = request.json
    user_message = data.get('question')
    session_id = data.get('session_id', 'default_session')
    
    if not user_message:
        return jsonify({"error": "No question provided"}), 400

    conversation_id = create_conversation_if_not_exists(session_id)
    save_message(conversation_id, "user", user_message)
    history_messages = get_recent_messages(conversation_id)

    docs = retrieve_docs(user_message)
    print(f"Retrieved documents: {len(docs)}")
    
    for doc in docs:
        print(f"  chunk_id: {doc['chunk_id']}, similarity: {doc['similarity']}")

    # Extract chunk IDs from retrieved documents
    relevant_chunk_ids = [doc['chunk_id'] for doc in docs if doc['chunk_id'] is not None]

    answer = generate_answer(user_message, docs, history_messages=history_messages)

    save_message(conversation_id, "assistant", answer, relevant_chunk_ids)

    return jsonify({"answer": answer})

@api_bp.route('/add-document', methods=['POST'])
def add_document():
    """Add document endpoint for uploading files or text content"""
    
    file = request.files.get('file')
    
    if file:
        # Handle file upload - get data from form
        title = request.form.get('title')
        source_type = request.form.get('sourceType')
        source_url = request.form.get('sourceUrl')
        category = request.form.get('category')
        version = request.form.get('version')
        
        content = load_file_content(file)
        if not content:
            return jsonify({"error": "Failed to read file content"}), 400
    else:
        # Handle JSON data
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        title = data.get('title')
        source_type = data.get('sourceType')
        source_url = data.get('sourceUrl')
        category = data.get('category')
        version = data.get('version')
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "Content is required"}), 400

    metadata = {
        "category": category,
        "version": version,
    }

    print(f"Received document: {title}")

    try:
        print(f"source_type: {source_type}")
        print(f"source_url: {source_url}")
        document_id = add_document_with_chunks(title, content, source_type, source_url, metadata)
        return jsonify({"message": "Document added successfully", "document_id": document_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def register_routes(app):
    """Register all API routes with the Flask app"""
    app.register_blueprint(api_bp)
