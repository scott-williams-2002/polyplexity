"""
SQLAlchemy ORM models for database schema.
Defines Thread, Message, and ExecutionTrace tables.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON,
    String, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session

Base = declarative_base()


class Thread(Base):
    """
    Thread model representing a conversation session.
    
    Attributes:
        thread_id: Primary key, unique thread identifier
        name: Human-readable thread name (5 words or less)
        created_at: Timestamp when thread was created
        updated_at: Timestamp when thread was last updated
        messages: Relationship to Message objects
    """
    __tablename__ = "threads"
    
    thread_id = Column(String, primary_key=True)
    name = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_threads_created_at", "created_at"),
        Index("idx_threads_updated_at", "updated_at"),
    )


class Message(Base):
    """
    Message model representing a user or assistant message.
    
    Attributes:
        id: Primary key UUID
        thread_id: Foreign key to Thread
        role: Message role ('user' or 'assistant')
        content: Message content text
        created_at: Timestamp when message was created
        message_index: Order index within thread
        thread: Relationship to Thread object
        execution_traces: Relationship to ExecutionTrace objects
    """
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    thread_id = Column(String, ForeignKey("threads.thread_id", ondelete="CASCADE"), nullable=False)
    role = Column(String, CheckConstraint("role IN ('user', 'assistant')"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    message_index = Column(Integer, nullable=False)
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
    execution_traces = relationship("ExecutionTrace", back_populates="message", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_messages_thread_id", "thread_id"),
        Index("idx_messages_thread_index", "thread_id", "message_index"),
        Index("idx_messages_created_at", "created_at"),
    )


class ExecutionTrace(Base):
    """
    ExecutionTrace model representing agent execution events.
    
    Attributes:
        id: Primary key UUID
        message_id: Foreign key to Message
        event_type: Type of event (e.g., 'node_call', 'reasoning', 'search')
        event_data: Event data as JSONB
        timestamp: Timestamp in milliseconds since epoch
        event_index: Order index within message
        message: Relationship to Message object
    """
    __tablename__ = "execution_traces"
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    message_id = Column(UUID(as_uuid=False), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    event_data = Column(JSON, nullable=True)
    timestamp = Column(BigInteger, nullable=False)
    event_index = Column(Integer, nullable=False)
    
    # Relationships
    message = relationship("Message", back_populates="execution_traces")
    
    # Indexes
    __table_args__ = (
        Index("idx_execution_traces_message_id", "message_id"),
        Index("idx_execution_traces_message_index", "message_id", "event_index"),
        Index("idx_execution_traces_timestamp", "timestamp"),
    )

