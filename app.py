#!/usr/bin/env python3
"""
Main application entry point for the RAG project.
Initializes Flask app with organized module structure.
"""

from flask import Flask
from flask_cors import CORS
from config.settings import get_config
import torch

def create_app(config_name=None):
    """Application factory pattern"""
    
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Validate configuration
    config.validate_config()
    
    # Initialize CORS
    CORS(app, origins=config.CORS_ORIGINS)
    
    # Register blueprints/routes
    from api.routes import register_routes
    register_routes(app)
    
    # GPU detection
    if torch.cuda.is_available():
        print(f"🚀 Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("🖥️  Using CPU")
    
    return app

def main():
    """Main entry point"""
    print("🌟 Starting RAG Project Backend...")
    
    # Create app
    app = create_app()
    config = get_config()
    
    # Run application
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG
    )

if __name__ == "__main__":
    main()