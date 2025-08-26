from __future__ import annotations

import os
from typing import Optional, AsyncGenerator, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from langchain_agent.agent import SimpleAgent

# Load environment variables
load_dotenv()

# Configuration from environment
VLLM_ENDPOINT = os.getenv("VLLM_ENDPOINT", "http://localhost:8000")
VLLM_MODEL = os.getenv("VLLM_MODEL", "gpt-3.5-turbo")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "9510"))
API_KEY = os.getenv("API_KEY")  # Optional API key for authentication
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))

# Language configuration
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "Chinese")
SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "Chinese,English").split(",")
AUTO_DETECT_LANGUAGE = os.getenv("AUTO_DETECT_LANGUAGE", "true").lower() == "true"

app = FastAPI(
    title="Agentic Service", 
    version="0.1.0",
    description="A multi-user document processing service with translation, RAG, analysis, and comparison capabilities",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional API key authentication
def verify_api_key(api_key: Optional[str] = Form(None)):
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@app.post("/chat")
async def unified_chat(
    query: str = Form(...),
    user: Optional[str] = Form(None),
    session: Optional[str] = Form(None),
    stream: bool = Form(False),
    files: Optional[List[UploadFile]] = File(None),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Unified chat endpoint that handles:
    - Text-only chat (no files)
    - Single file upload (1 file)
    - Multiple file upload (2+ files)
    - All 6 processing modes (translation, RAG, summarization, analysis, extraction, comparison)
    - Streaming and non-streaming responses
    - Multi-user session management
    """
    user = user or "default_user"
    session = session or "default_session"
    
    # Handle file uploads if provided
    primary_file_path = None
    if files:
        # Validate file sizes
        for file in files:
            if file.size and file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=413, 
                    detail=f"File '{file.filename}' too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
                )

        # Save files to disk
        os.makedirs(".tmp_uploads", exist_ok=True)
        tmp_paths = []
        
        for file in files:
            tmp_path = os.path.join(".tmp_uploads", file.filename)
            with open(tmp_path, "wb") as f:
                f.write(await file.read())
            tmp_paths.append(tmp_path)
        
        # Use the first file as primary (agent handles multi-file logic internally)
        primary_file_path = tmp_paths[0] if tmp_paths else None

    # Create agent and process request
    agent = SimpleAgent(llm_endpoint=VLLM_ENDPOINT, model=VLLM_MODEL)

    if stream:
        def generator():
            for chunk in agent.run(
                query=query, 
                file_path=primary_file_path, 
                stream=True, 
                user_id=user, 
                session_id=session
            ):
                yield chunk
        return StreamingResponse(generator(), media_type="text/plain")
    else:
        # agent.run returns a generator even when stream=False (for persistence)
        # So we need to consume it to get the full answer
        response_gen = agent.run(
            query=query, 
            file_path=primary_file_path, 
            stream=False, 
            user_id=user, 
            session_id=session
        )
        answer = "".join(response_gen)
        return JSONResponse({"answer": answer})


# Backward compatibility endpoints (deprecated but functional)
@app.post("/chat-with-file")
async def chat_with_file_deprecated(
    query: str = Form(...),
    user: Optional[str] = Form(None),
    session: Optional[str] = Form(None),
    stream: bool = Form(False),
    upload: UploadFile = File(...),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """Deprecated: Use /chat with files parameter instead."""
    return await unified_chat(query, user, session, stream, [upload], api_key)


@app.post("/chat-with-multiple-files")
async def chat_with_multiple_files_deprecated(
    query: str = Form(...),
    user: Optional[str] = Form(None),
    session: Optional[str] = Form(None),
    stream: bool = Form(False),
    uploads: List[UploadFile] = File(...),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """Deprecated: Use /chat with files parameter instead."""
    return await unified_chat(query, user, session, stream, uploads, api_key)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Agentic Service", "version": "0.1.0"}


@app.get("/config")
async def get_config(api_key: Optional[str] = Depends(verify_api_key)):
    """Get current configuration (requires API key if set)."""
    return {
        "vllm_endpoint": VLLM_ENDPOINT,
        "vllm_model": VLLM_MODEL,
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "api_key_required": API_KEY is not None,
        "cors_origins": ALLOWED_ORIGINS,
        "default_language": DEFAULT_LANGUAGE,
        "supported_languages": SUPPORTED_LANGUAGES,
        "auto_detect_language": AUTO_DETECT_LANGUAGE
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
