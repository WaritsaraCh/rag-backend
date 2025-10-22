from multiprocessing.connection import answer_challenge
import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from loaders import load_file_content
from llm import generate_answer
from db import (
    save_message,
    create_conversation_if_not_exists,
    add_document_with_chunks,
    retrieve_docs,
    get_recent_messages
)
import torch

if torch.cuda.is_available():
    device = "cuda"
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({"message": "Hello, World!"})


@app.route('/chat', methods=['POST'])
def chat():
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


@app.route('/add-document', methods=['POST'])
def document():
   
    file = request.files.get('file')
    
    if file:
        # Handle file upload - get data from form
        title = request.form.get('title')
        source_type = request.form.get('sourceType')
        source_url = request.form.get('sourceUrl')
        category = request.form.get('category')
        version = request.form.get('version')
        
        # print(f"Received file: {file.filename}")
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

if __name__ == "__main__":
    print("🌟 Starting Flask application...")
    app.run(host="0.0.0.0", port=5000, debug=True)
