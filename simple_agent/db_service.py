"""
Database service layer for the Agentic Service.

This module provides high-level operations for:
- User and session management
- Chat history operations
- Document and chunk management
- Processing cache operations
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Generator
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from .database import (
    SessionLocal, User, Session as DBSession, ChatHistory, Document, 
    DocumentChunk, ProcessingCache, VectorEmbedding, FileStorage
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """High-level database operations for the agentic service."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()
    
    def commit(self):
        """Commit current transaction."""
        self.db.commit()
    
    def rollback(self):
        """Rollback current transaction."""
        self.db.rollback()
    
    # User management
    def get_or_create_user(self, user_id: str, username: Optional[str] = None) -> User:
        """Get existing user or create new one."""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id, username=username or user_id)
            self.db.add(user)
            self.db.commit()
            logger.info(f"Created new user: {user_id}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    def update_user_last_login(self, user_id: str):
        """Update user's last login timestamp."""
        user = self.get_user(user_id)
        if user:
            user.last_login = datetime.utcnow()
            self.db.commit()
    
    # Session management
    def get_or_create_session(self, user_id: str, session_id: str) -> DBSession:
        """Get existing session or create new one."""
        # Ensure user exists
        self.get_or_create_user(user_id)
        
        session = self.db.query(DBSession).filter(
            and_(DBSession.user_id == user_id, DBSession.session_id == session_id)
        ).first()
        
        if not session:
            session = DBSession(user_id=user_id, session_id=session_id)
            self.db.add(session)
            self.db.commit()
            logger.info(f"Created new session: {user_id}/{session_id}")
        else:
            # Update last activity
            session.last_activity = datetime.utcnow()
            self.db.commit()
        
        return session
    
    def get_session(self, user_id: str, session_id: str) -> Optional[DBSession]:
        """Get session by user_id and session_id."""
        return self.db.query(DBSession).filter(
            and_(DBSession.user_id == user_id, DBSession.session_id == session_id)
        ).first()
    
    def get_user_sessions(self, user_id: str) -> List[DBSession]:
        """Get all sessions for a user."""
        return self.db.query(DBSession).filter(
            DBSession.user_id == user_id
        ).order_by(desc(DBSession.last_activity)).all()
    
    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up sessions older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        old_sessions = self.db.query(DBSession).filter(
            DBSession.last_activity < cutoff_date
        ).all()
        
        for session in old_sessions:
            self.db.delete(session)
        
        self.db.commit()
        logger.info(f"Cleaned up {len(old_sessions)} old sessions")
    
    # Chat history management
    def add_chat_message(self, user_id: str, session_id: str, role: str, content: str, 
                        metadata: Optional[Dict] = None) -> ChatHistory:
        """Add a new chat message."""
        session = self.get_or_create_session(user_id, session_id)
        
        chat_msg = ChatHistory(
            session_id=session.id,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.db.add(chat_msg)
        self.db.commit()
        
        # Update session last activity
        session.last_activity = datetime.utcnow()
        self.db.commit()
        
        return chat_msg
    
    def get_chat_history(self, user_id: str, session_id: str, 
                        limit: Optional[int] = None) -> List[ChatHistory]:
        """Get chat history for a session."""
        session = self.get_session(user_id, session_id)
        if not session:
            return []
        
        query = self.db.query(ChatHistory).filter(
            ChatHistory.session_id == session.id
        ).order_by(ChatHistory.timestamp)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_recent_chat_history(self, user_id: str, session_id: str, 
                               message_count: int = 10) -> List[ChatHistory]:
        """Get recent chat history for context."""
        session = self.get_session(user_id, session_id)
        if not session:
            return []
        
        return self.db.query(ChatHistory).filter(
            ChatHistory.session_id == session.id
        ).order_by(desc(ChatHistory.timestamp)).limit(message_count).all()
    
    # Document management
    def add_document(self, user_id: str, session_id: str, filename: str, 
                    file_hash: str, file_size: Optional[int] = None,
                    file_type: Optional[str] = None, mime_type: Optional[str] = None,
                    metadata: Optional[Dict] = None) -> Document:
        """Add a new document."""
        session = self.get_or_create_session(user_id, session_id)
        
        # Check if document already exists
        existing_doc = self.db.query(Document).filter(
            and_(Document.session_id == session.id, Document.file_hash == file_hash)
        ).first()
        
        if existing_doc:
            # Update existing document
            existing_doc.original_filename = filename
            existing_doc.file_size = file_size
            existing_doc.file_type = file_type
            existing_doc.mime_type = mime_type
            if metadata:
                existing_doc.document_metadata.update(metadata)
            existing_doc.processed_at = datetime.utcnow()
            self.db.commit()
            return existing_doc
        
        # Create new document
        doc = Document(
            session_id=session.id,
            original_filename=filename,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            metadata=metadata or {}
        )
        
        self.db.add(doc)
        self.db.commit()
        
        return doc
    
    def get_document(self, user_id: str, session_id: str, file_hash: str) -> Optional[Document]:
        """Get document by hash."""
        session = self.get_session(user_id, session_id)
        if not session:
            return None
        
        return self.db.query(Document).filter(
            and_(Document.session_id == session.id, Document.file_hash == file_hash)
        ).first()
    
    def add_document_chunks(self, document_id: int, chunks: List[str], 
                           chunk_metadata: Optional[List[Dict]] = None) -> List[DocumentChunk]:
        """Add chunks for a document."""
        doc_chunks = []
        
        for i, chunk_text in enumerate(chunks):
            chunk_hash = hashlib.sha256(chunk_text.encode()).hexdigest()
            metadata = chunk_metadata[i] if chunk_metadata and i < len(chunk_metadata) else {}
            
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=i,
                chunk_text=chunk_text,
                chunk_hash=chunk_hash,
                chunk_size=len(chunk_text),
                chunk_metadata=metadata
            )
            
            self.db.add(chunk)
            doc_chunks.append(chunk)
        
        self.db.commit()
        return doc_chunks
    
    def get_document_chunks(self, document_id: int) -> List[DocumentChunk]:
        """Get all chunks for a document."""
        return self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
    
    # Processing cache management
    def get_processing_cache(self, user_id: str, session_id: str, 
                           document_hash: str, processing_mode: str) -> Optional[ProcessingCache]:
        """Get processing cache for a document and mode."""
        session = self.get_session(user_id, session_id)
        if not session:
            return None
        
        cache = self.db.query(ProcessingCache).filter(
            and_(
                ProcessingCache.session_id == session.id,
                ProcessingCache.document_hash == document_hash,
                ProcessingCache.processing_mode == processing_mode
            )
        ).first()
        
        # Check if cache is expired
        if cache and cache.expires_at and cache.expires_at < datetime.utcnow():
            self.db.delete(cache)
            self.db.commit()
            return None
        
        return cache
    
    def set_processing_cache(self, user_id: str, session_id: str, document_hash: str,
                           processing_mode: str, cache_data: Dict, 
                           expires_in_hours: Optional[int] = 24) -> ProcessingCache:
        """Set processing cache for a document and mode."""
        session = self.get_or_create_session(user_id, session_id)
        
        # Check if cache already exists
        existing_cache = self.get_processing_cache(user_id, session_id, document_hash, processing_mode)
        
        if existing_cache:
            # Update existing cache
            existing_cache.cache_data = cache_data
            existing_cache.updated_at = datetime.utcnow()
            if expires_in_hours:
                existing_cache.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            self.db.commit()
            return existing_cache
        
        # Create new cache
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        cache = ProcessingCache(
            session_id=session.id,
            document_hash=document_hash,
            processing_mode=processing_mode,
            cache_data=cache_data,
            expires_at=expires_at
        )
        
        self.db.add(cache)
        self.db.commit()
        
        return cache
    
    def cleanup_expired_caches(self):
        """Clean up expired processing caches."""
        expired_caches = self.db.query(ProcessingCache).filter(
            ProcessingCache.expires_at < datetime.utcnow()
        ).all()
        
        for cache in expired_caches:
            self.db.delete(cache)
        
        self.db.commit()
        logger.info(f"Cleaned up {len(expired_caches)} expired caches")
    
    # Vector embeddings
    def add_vector_embedding(self, chunk_id: int, embedding_model: str, 
                           embedding_vector: List[float]) -> VectorEmbedding:
        """Add vector embedding for a chunk."""
        # Check if embedding already exists
        existing = self.db.query(VectorEmbedding).filter(
            and_(
                VectorEmbedding.chunk_id == chunk_id,
                VectorEmbedding.embedding_model == embedding_model
            )
        ).first()
        
        if existing:
            # Update existing embedding
            existing.embedding_vector = embedding_vector
            self.db.commit()
            return existing
        
        # Create new embedding
        embedding = VectorEmbedding(
            chunk_id=chunk_id,
            embedding_model=embedding_model,
            embedding_vector=embedding_vector
        )
        
        self.db.add(embedding)
        self.db.commit()
        
        return embedding
    
    def get_vector_embeddings(self, chunk_id: int, embedding_model: str) -> Optional[VectorEmbedding]:
        """Get vector embedding for a chunk and model."""
        return self.db.query(VectorEmbedding).filter(
            and_(
                VectorEmbedding.chunk_id == chunk_id,
                VectorEmbedding.embedding_model == embedding_model
            )
        ).first()
    
    # File storage
    def add_file_storage(self, document_id: int, storage_backend: str, 
                        storage_path: Optional[str] = None, storage_url: Optional[str] = None,
                        storage_metadata: Optional[Dict] = None) -> FileStorage:
        """Add file storage information."""
        # Check if storage info already exists
        existing = self.db.query(FileStorage).filter(
            and_(
                FileStorage.document_id == document_id,
                FileStorage.storage_backend == storage_backend
            )
        ).first()
        
        if existing:
            # Update existing storage info
            existing.storage_path = storage_path
            existing.storage_url = storage_url
            if storage_metadata:
                existing.storage_metadata.update(storage_metadata)
            self.db.commit()
            return existing
        
        # Create new storage info
        storage = FileStorage(
            document_id=document_id,
            storage_backend=storage_backend,
            storage_path=storage_path,
            storage_url=storage_url,
            storage_metadata=storage_metadata or {}
        )
        
        self.db.add(storage)
        self.db.commit()
        
        return storage
    
    # Utility methods
    def get_session_stats(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        session = self.get_session(user_id, session_id)
        if not session:
            return {}
        
        chat_count = self.db.query(ChatHistory).filter(
            ChatHistory.session_id == session.id
        ).count()
        
        doc_count = self.db.query(Document).filter(
            Document.session_id == session.id
        ).count()
        
        cache_count = self.db.query(ProcessingCache).filter(
            ProcessingCache.session_id == session.id
        ).count()
        
        return {
            "chat_messages": chat_count,
            "documents": doc_count,
            "processing_caches": cache_count,
            "created_at": session.created_at,
            "last_activity": session.last_activity
        }
    
    def search_chat_history(self, user_id: str, session_id: str, 
                           query: str, limit: int = 10) -> List[ChatHistory]:
        """Search chat history using full-text search."""
        session = self.get_session(user_id, session_id)
        if not session:
            return []
        
        # Use PostgreSQL full-text search
        search_query = func.to_tsquery('english', query)
        
        results = self.db.query(ChatHistory).filter(
            and_(
                ChatHistory.session_id == session.id,
                func.to_tsvector('english', ChatHistory.content).op('@@')(search_query)
            )
        ).order_by(
            func.ts_rank(func.to_tsvector('english', ChatHistory.content), search_query).desc()
        ).limit(limit).all()
        
        return results


# Convenience functions for backward compatibility
def get_db_service() -> DatabaseService:
    """Get a database service instance."""
    return DatabaseService()


def add_chat_message(user_id: str, session_id: str, role: str, content: str, 
                    metadata: Optional[Dict] = None) -> ChatHistory:
    """Add a chat message using a temporary database service."""
    with DatabaseService() as db_service:
        return db_service.add_chat_message(user_id, session_id, role, content, metadata)


def get_chat_history(user_id: str, session_id: str, limit: Optional[int] = None) -> List[ChatHistory]:
    """Get chat history using a temporary database service."""
    with DatabaseService() as db_service:
        return db_service.get_chat_history(user_id, session_id, limit)


def get_or_create_session(user_id: str, session_id: str) -> DBSession:
    """Get or create a session using a temporary database service."""
    with DatabaseService() as db_service:
        return db_service.get_or_create_session(user_id, session_id)

