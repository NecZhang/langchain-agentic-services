"""
Database models and configuration for the Agentic Service.

This module provides SQLAlchemy models for all data types including:
- Users and sessions
- Chat history
- Document metadata and chunks
- Processing caches
- Vector embeddings
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, 
    DateTime, BigInteger, ForeignKey, UniqueConstraint, Index,
    Text, JSON, ARRAY, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.sql import func
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://agentic_user:secure_password_change_me@localhost:5432/agentic_service"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=os.getenv("DB_ECHO", "false").lower() == "true"
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


class User(Base):
    """User model for storing user information."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255))
    email = Column(String(255))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True)
    user_metadata = Column(JSONB, default={})
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(user_id='{self.user_id}', username='{self.username}')>"


class Session(Base):
    """Session model for storing user sessions."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False)
    session_id = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_activity = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    session_metadata = Column(JSONB, default={})
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    chat_history = relationship("ChatHistory", back_populates="session", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")
    processing_caches = relationship("ProcessingCache", back_populates="session", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_user_session"),
        Index("idx_sessions_user_session", "user_id", "session_id"),
        Index("idx_sessions_last_activity", "last_activity"),
    )
    
    def __repr__(self):
        return f"<Session(user_id='{self.user_id}', session_id='{self.session_id}')>"


class ChatHistory(Base):
    """Chat history model for storing conversation messages."""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    chat_metadata = Column(JSONB, default={})
    
    # Relationships
    session = relationship("Session", back_populates="chat_history")
    
    # Constraints
    __table_args__ = (
        Index("idx_chat_history_session_timestamp", "session_id", "timestamp"),
        Index("idx_chat_content_search", "content", postgresql_using="gin"),
    )
    
    def __repr__(self):
        return f"<ChatHistory(role='{self.role}', timestamp='{self.timestamp}')>"


class Document(Base):
    """Document model for storing file metadata."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False)
    file_size = Column(BigInteger)
    file_type = Column(String(100))
    mime_type = Column(String(200))
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    processed_at = Column(TIMESTAMP(timezone=True))
    status = Column(String(50), default="uploaded")
    document_metadata = Column(JSONB, default={})
    
    # Relationships
    session = relationship("Session", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    file_storage = relationship("FileStorage", back_populates="document", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("session_id", "file_hash", name="uq_session_file"),
        Index("idx_documents_session_hash", "session_id", "file_hash"),
        Index("idx_documents_hash", "file_hash"),
    )
    
    def __repr__(self):
        return f"<Document(filename='{self.original_filename}', hash='{self.file_hash}')>"


class DocumentChunk(Base):
    """Document chunk model for storing processed text chunks."""
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_hash = Column(String(64), nullable=False)
    chunk_size = Column(Integer)
    chunk_metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    vector_embeddings = relationship("VectorEmbedding", back_populates="chunk", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),
        Index("idx_chunks_document_index", "document_id", "chunk_index"),
    )
    
    def __repr__(self):
        return f"<DocumentChunk(index={self.chunk_index}, size={self.chunk_size})>"


class ProcessingCache(Base):
    """Processing cache model for storing RAG and other processing results."""
    __tablename__ = "processing_caches"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    document_hash = Column(String(64), nullable=False)
    processing_mode = Column(String(100), nullable=False)
    cache_data = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    session = relationship("Session", back_populates="processing_caches")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("session_id", "document_hash", "processing_mode", name="uq_session_doc_mode"),
        Index("idx_caches_session_mode", "session_id", "processing_mode"),
    )
    
    def __repr__(self):
        return f"<ProcessingCache(mode='{self.processing_mode}', doc_hash='{self.document_hash}')>"


class VectorEmbedding(Base):
    """Vector embedding model for storing semantic search vectors."""
    __tablename__ = "vector_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=False)
    embedding_model = Column(String(100), nullable=False)
    embedding_vector = Column(ARRAY(Float), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    chunk = relationship("DocumentChunk", back_populates="vector_embeddings")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("chunk_id", "embedding_model", name="uq_chunk_model"),
        Index("idx_embeddings_chunk_model", "chunk_id", "embedding_model"),
    )
    
    def __repr__(self):
        return f"<VectorEmbedding(model='{self.embedding_model}', vector_size={len(self.embedding_vector)})>"


class FileStorage(Base):
    """File storage model for storing file location information."""
    __tablename__ = "file_storage"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    storage_backend = Column(String(50), nullable=False, default="local")
    storage_path = Column(String(1000))
    storage_url = Column(String(1000))
    storage_metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="file_storage")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("document_id", "storage_backend", name="uq_document_storage"),
    )
    
    def __repr__(self):
        return f"<FileStorage(backend='{self.storage_backend}', path='{self.storage_path}')>"


# Database utility functions
def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def create_tables():
    """Create all tables if they don't exist."""
    init_db()


def drop_tables():
    """Drop all tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)


# Database health check
def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
            conn.commit()
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False


if __name__ == "__main__":
    # Create tables when run directly
    print("Creating database tables...")
    create_tables()
    print("Database tables created successfully!")

