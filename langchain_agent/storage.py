"""Per-user/session storage for documents, chunk caches, retriever indices, and chat history.

All data is stored under a base directory (default: .data). Structure:

.data/
  users/
    <user_id>/
      sessions/
        <session_id>/
          chat_history.jsonl           # one JSON per line: {role, content, ts}
          uploads/
            <original_filename>        # copied user file
          caches/
            <doc_hash>_<mode>/
              chunks.json              # list[str]
              tfidf_vectorizer.joblib  # persisted vectorizer
              doc_vectors.npz          # csr_matrix saved via scipy.sparse
              nn_index.joblib          # NearestNeighbors index
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import joblib

# Production-ready default paths - use environment variables for security
# nosec B108 - These are fallback defaults that can be overridden via environment variables
DEFAULT_BASE_DIR = Path(os.environ.get("AGENTIC_DATA_DIR", "/var/lib/agentic-service"))  # nosec B108
DEFAULT_TEMP_DIR = Path(os.environ.get("AGENTIC_TEMP_DIR", "/tmp/agentic-uploads"))  # nosec B108

# Fallback to project directory only for development
if not DEFAULT_BASE_DIR.exists() and not os.environ.get("AGENTIC_DATA_DIR"):
    DEFAULT_BASE_DIR = Path(".data")
if not DEFAULT_TEMP_DIR.exists() and not os.environ.get("AGENTIC_TEMP_DIR"):
    DEFAULT_TEMP_DIR = Path(".tmp_uploads")

def get_storage_paths() -> Tuple[Path, Path]:
    """Get configured storage paths from environment variables."""
    data_dir = os.environ.get("AGENTIC_DATA_DIR")
    temp_dir = os.environ.get("AGENTIC_TEMP_DIR")
    
    if data_dir:
        data_path = Path(data_dir)
    else:
        data_path = DEFAULT_BASE_DIR
        
    if temp_dir:
        temp_path = Path(temp_dir)
    else:
        temp_path = DEFAULT_TEMP_DIR
    
    return data_path, temp_path


@dataclass
class StoragePaths:
    base_dir: Path
    user_dir: Path
    session_dir: Path
    history_path: Path
    uploads_dir: Path
    caches_dir: Path


def ensure_session_dirs(user_id: str, session_id: str, base_dir: Optional[Path] = None) -> StoragePaths:
    if base_dir is None:
        base_dir, _ = get_storage_paths()
    
    base_dir = Path(base_dir)
    user_dir = base_dir / "users" / user_id
    session_dir = user_dir / "sessions" / session_id
    uploads_dir = session_dir / "uploads"
    caches_dir = session_dir / "caches"
    history_path = session_dir / "chat_history.jsonl"
    
    # Ensure directories exist with proper permissions
    for d in [user_dir, session_dir, uploads_dir, caches_dir]:
        d.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions for production
        # Use environment variables to determine if this is a production path
        is_production_path = (
            str(d).startswith(os.environ.get("AGENTIC_DATA_DIR", "/var/lib")) or  # nosec B108
            str(d).startswith(os.environ.get("AGENTIC_TEMP_DIR", "/tmp"))  # nosec B108
        )
        if is_production_path:
            d.chmod(0o750)  # Owner: rwx, Group: rx, Others: none
    
    return StoragePaths(
        base_dir=base_dir,
        user_dir=user_dir,
        session_dir=session_dir,
        history_path=history_path,
        uploads_dir=uploads_dir,
        caches_dir=caches_dir,
    )


def compute_file_hash(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def copy_upload(paths: StoragePaths, src_path: str) -> Path:
    dest = paths.uploads_dir / Path(src_path).name
    if not dest.exists():
        shutil.copy2(src_path, dest)
    return dest


def append_chat_message(paths: StoragePaths, role: str, content: str) -> None:
    entry = {"ts": int(time.time()), "role": role, "content": content}
    with open(paths.history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_chat_history(paths: StoragePaths, max_messages: Optional[int] = None) -> List[dict]:
    if not paths.history_path.exists():
        return []
    messages: List[dict] = []
    with open(paths.history_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                messages.append(json.loads(line))
            except Exception as e:  # nosec B112
                # Log the error but continue processing other lines
                import logging
                logging.warning(f"Failed to parse chat history line: {e}")
                continue
    if max_messages is not None:
        messages = messages[-max_messages:]
    return messages


def cache_key(doc_hash: str, mode: str) -> str:
    return f"{doc_hash}_{mode}"


def cache_dir_for(paths: StoragePaths, key: str) -> Path:
    d = paths.caches_dir / key
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_chunks(paths: StoragePaths, key: str, chunks: List[str]) -> None:
    d = cache_dir_for(paths, key)
    with open(d / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)


def load_chunks(paths: StoragePaths, key: str) -> Optional[List[str]]:
    p = paths.caches_dir / key / "chunks.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_retriever(paths: StoragePaths, key: str, vectorizer: TfidfVectorizer, doc_vectors: sparse.csr_matrix, nn: NearestNeighbors) -> None:
    d = cache_dir_for(paths, key)
    joblib.dump(vectorizer, d / "tfidf_vectorizer.joblib")
    sparse.save_npz(d / "doc_vectors.npz", doc_vectors)
    joblib.dump(nn, d / "nn_index.joblib")


def load_retriever(paths: StoragePaths, key: str) -> Optional[Tuple[TfidfVectorizer, sparse.csr_matrix, NearestNeighbors]]:
    d = paths.caches_dir / key
    vec_path = d / "tfidf_vectorizer.joblib"
    mat_path = d / "doc_vectors.npz"
    nn_path = d / "nn_index.joblib"
    if not (vec_path.exists() and mat_path.exists() and nn_path.exists()):
        return None
    vectorizer: TfidfVectorizer = joblib.load(vec_path)
    doc_vectors: sparse.csr_matrix = sparse.load_npz(mat_path)
    nn: NearestNeighbors = joblib.load(nn_path)
    return vectorizer, doc_vectors, nn


def last_doc_key_path(paths: StoragePaths) -> Path:
    return paths.session_dir / "last_doc_key.json"


def set_last_doc_key(paths: StoragePaths, key: str) -> None:
    p = last_doc_key_path(paths)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"key": key}, f)


def get_last_doc_key(paths: StoragePaths) -> Optional[str]:
    p = last_doc_key_path(paths)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("key")
    except Exception:
        return None


def get_all_cached_documents(paths: StoragePaths) -> List[Tuple[str, List[str]]]:
    """Get all cached documents from the session.
    
    Returns
    -------
    List[Tuple[str, List[str]]]
        List of (cache_key, chunks) pairs for all cached documents in the session.
    """
    cached_docs = []
    if not paths.caches_dir.exists():
        return cached_docs
    
    # Iterate through all cache directories
    for cache_dir in paths.caches_dir.iterdir():
        if cache_dir.is_dir():
            chunks_file = cache_dir / "chunks.json"
            if chunks_file.exists():
                try:
                    with open(chunks_file, "r", encoding="utf-8") as f:
                        chunks = json.load(f)
                        cached_docs.append((cache_dir.name, chunks))
                except (json.JSONDecodeError, IOError):
                    # Skip corrupted cache files
                    continue
    
    return cached_docs
