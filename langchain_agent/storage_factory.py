"""
Storage Factory for Agentic Service.

This module provides a unified interface for storage operations,
automatically selecting between file-based and database storage
based on environment configuration.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any, Generator
from abc import ABC, abstractmethod

# Import both storage backends
from .storage import (
    ensure_session_dirs as file_ensure_session_dirs, append_chat_message as file_append_chat_message,
    load_chat_history as file_load_chat_history, compute_file_hash,
    copy_upload, cache_key, save_chunks, load_chunks,
    save_retriever, load_retriever, set_last_doc_key,
    get_last_doc_key, get_all_cached_documents
)

from .db_service import (
    DatabaseService, add_chat_message as db_add_chat_message,
    get_chat_history as db_get_chat_history, get_or_create_session as db_get_or_create_session
)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def append_chat_message(self, storage_paths, role: str, content: str) -> None:
        """Add a chat message to storage."""
        pass
    
    @abstractmethod
    def load_chat_history(self, storage_paths, limit: Optional[int] = None, max_messages: Optional[int] = None) -> List[Dict]:
        """Load chat history from storage."""
        pass
    
    @abstractmethod
    def get_or_create_session(self, user_id: str, session_id: str) -> Any:
        """Get or create a session."""
        pass


class FileStorageBackend(StorageBackend):
    """File-based storage backend."""
    
    def append_chat_message(self, storage_paths, role: str, content: str) -> None:
        """Add chat message to file storage."""
        return file_append_chat_message(storage_paths, role, content)
    
    def load_chat_history(self, storage_paths, limit: Optional[int] = None, max_messages: Optional[int] = None) -> List[Dict]:
        """Load chat history from file storage."""
        # Use max_messages if provided, otherwise fall back to limit
        actual_limit = max_messages if max_messages is not None else limit
        return file_load_chat_history(storage_paths, actual_limit)
    
    def get_or_create_session(self, user_id: str, session_id: str) -> Any:
        """Get or create session in file storage."""
        # For file storage, we return the storage paths
        from .storage import get_storage_paths
        base_dir, temp_dir = get_storage_paths()
        return ensure_session_dirs(user_id, session_id, base_dir)


class DatabaseStorageBackend(StorageBackend):
    """PostgreSQL database storage backend."""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    def append_chat_message(self, storage_paths, role: str, content: str) -> None:
        """Add chat message to database."""
        # Extract user_id and session_id from storage_paths
        user_id = getattr(storage_paths, 'user_id', 'default_user')
        session_id = getattr(storage_paths, 'session_id', 'default_session')
        
        # If storage_paths doesn't have user_id/session_id, try to extract from path
        if not hasattr(storage_paths, 'user_id'):
            # Try to extract from the path structure
            path_str = str(storage_paths.base_dir)
            if '/users/' in path_str:
                parts = path_str.split('/users/')
                if len(parts) > 1:
                    user_part = parts[1].split('/')[0]
                    user_id = user_part
                    if '/sessions/' in path_str:
                        session_part = path_str.split('/sessions/')
                        if len(session_part) > 1:
                            session_id = session_part[1].split('/')[0]
        
        return db_add_chat_message(user_id, session_id, role, content)
    
    def load_chat_history(self, storage_paths, limit: Optional[int] = None, max_messages: Optional[int] = None) -> List[Dict]:
        """Load chat history from database."""
        # Extract user_id and session_id from storage_paths
        user_id = getattr(storage_paths, 'user_id', 'default_user')
        session_id = getattr(storage_paths, 'session_id', 'default_session')
        
        # If storage_paths doesn't have user_id/session_id, try to extract from path
        if not hasattr(storage_paths, 'user_id'):
            # Try to extract from the path structure
            path_str = str(storage_paths.base_dir)
            if '/users/' in path_str:
                parts = path_str.split('/users/')
                if len(parts) > 1:
                    user_part = parts[1].split('/')[0]
                    user_id = user_part
                    if '/sessions/' in path_str:
                        session_part = path_str.split('/sessions/')
                        if len(session_part) > 1:
                            session_id = session_part[1].split('/')[0]
        
        # Use max_messages if provided, otherwise fall back to limit
        actual_limit = max_messages if max_messages is not None else limit
        
        # Convert database objects to dict format for compatibility
        db_history = db_get_chat_history(user_id, session_id, actual_limit)
        return [
            {
                'role': msg.role,
                'content': msg.content,
                'ts': msg.timestamp.timestamp() if msg.timestamp else None
            }
            for msg in db_history
        ]
    
    def get_or_create_session(self, user_id: str, session_id: str) -> Any:
        """Get or create session in database."""
        return db_get_or_create_session(user_id, session_id)


def get_storage_backend() -> StorageBackend:
    """Get the appropriate storage backend based on environment configuration."""
    storage_backend = os.getenv("STORAGE_BACKEND", "auto").lower()
    
    # Auto-detect based on environment
    if storage_backend == "auto":
        # Check if we're in Docker or have database configuration
        if os.getenv("DATABASE_URL") and os.path.exists("/.dockerenv"):
            storage_backend = "database"
        else:
            storage_backend = "file"
    
    if storage_backend == "database":
        return DatabaseStorageBackend()
    else:
        return FileStorageBackend()


# Convenience functions that automatically use the right backend
def append_chat_message(storage_paths, role: str, content: str) -> None:
    """Add chat message using the appropriate storage backend."""
    backend = get_storage_backend()
    return backend.append_chat_message(storage_paths, role, content)


def load_chat_history(storage_paths, limit: Optional[int] = None, max_messages: Optional[int] = None) -> List[Dict]:
    """Load chat history using the appropriate storage backend."""
    backend = get_storage_backend()
    return backend.load_chat_history(storage_paths, limit, max_messages)


def get_or_create_session(user_id: str, session_id: str) -> Any:
    """Get or create session using the appropriate storage backend."""
    backend = get_storage_backend()
    return backend.get_or_create_session(user_id, session_id)


def ensure_session_dirs(user_id: str, session_id: str) -> Any:
    """Ensure session directories exist and return storage paths.
    
    For database backend, this returns a mock object with user_id and session_id attributes.
    For file backend, this creates directories and returns StoragePaths.
    """
    backend = get_storage_backend()
    if isinstance(backend, DatabaseStorageBackend):
        # For database backend, return a mock object with the required attributes
        class MockStoragePaths:
            def __init__(self, user_id, session_id):
                self.user_id = user_id
                self.session_id = session_id
        return MockStoragePaths(user_id, session_id)
    else:
        # For file backend, use the original function
        return file_ensure_session_dirs(user_id, session_id)


# Export all the original functions for backward compatibility
__all__ = [
    'StorageBackend', 'FileStorageBackend', 'DatabaseStorageBackend',
    'get_storage_backend', 'append_chat_message', 'load_chat_history',
    'get_or_create_session',
    # File storage functions
    'ensure_session_dirs', 'compute_file_hash', 'copy_upload',
    'cache_key', 'save_chunks', 'load_chunks', 'save_retriever',
    'load_retriever', 'set_last_doc_key', 'get_last_doc_key',
    'get_all_cached_documents'
]
