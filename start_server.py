#!/usr/bin/env python3
"""
Startup script for the Agentic Service API server.
This script loads configuration from .env and starts the server.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    """Start the Agentic Service API server."""
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "9211"))
    
    # Check if required environment variables are set
    vllm_endpoint = os.getenv("VLLM_ENDPOINT")
    vllm_model = os.getenv("VLLM_MODEL")
    
    if not vllm_endpoint:
        print("⚠️  Warning: VLLM_ENDPOINT not set in .env file. Using default: http://localhost:8000")
    
    if not vllm_model:
        print("⚠️  Warning: VLLM_MODEL not set in .env file. Using default: gpt-3.5-turbo")
    
    print("🚀 Starting Agentic Service API...")
    print(f"📡 Server: http://{host}:{port}")
    print(f"🤖 vLLM Endpoint: {vllm_endpoint or 'http://localhost:8000'}")
    print(f"🧠 Model: {vllm_model or 'gpt-3.5-turbo'}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print("=" * 50)
    
    try:
        import uvicorn
        from api import app
        
        # Development: reload=True for auto-reload on code changes
        # Production: reload=False for stability and performance
        uvicorn.run(
            app, 
            host=host, 
            port=port,
            reload=False,  # Disable auto-reload to prevent hanging
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")
    except ImportError as e:
        print(f"❌ Error importing required modules: {e}")
        print("💡 Make sure you have installed all dependencies with: uv sync")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
