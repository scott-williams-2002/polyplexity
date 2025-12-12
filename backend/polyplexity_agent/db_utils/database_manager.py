"""
Database manager using SQLAlchemy ORM.
Consolidates all database operations (migrations and CRUD) into a single entry point.
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from polyplexity_agent.config.secrets import get_postgres_connection_string
from .db_schema import Base, ExecutionTrace, Message, Thread


class DatabaseManager:
    """
    Centralized database manager for all database operations.
    Handles migrations, CRUD operations for threads, messages, and execution traces.
    """
    
    def __init__(self):
        """
        Initialize DatabaseManager with SQLAlchemy engine and session factory.
        """
        conn_string = get_postgres_connection_string()
        if not conn_string:
            raise ValueError("POSTGRES_CONNECTION_STRING not set")
        
        # Ensure connection string uses postgresql+psycopg:// format for SQLAlchemy 2.0
        # Handle both postgres:// and postgresql:// formats
        original_conn_string = conn_string
        if conn_string.startswith("postgres://"):
            conn_string = conn_string.replace("postgres://", "postgresql+psycopg://", 1)
        elif conn_string.startswith("postgresql://") and "+psycopg" not in conn_string:
            conn_string = conn_string.replace("postgresql://", "postgresql+psycopg://", 1)
        
        # Debug: log connection string format (without password)
        if original_conn_string != conn_string:
            from polyplexity_agent.logging import get_logger
            logger = get_logger(__name__)
            logger.debug("connection_string_converted", original_format=original_conn_string.split("@")[0], new_format=conn_string.split("@")[0])
        
        self.engine = create_engine(conn_string, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy Session instance
        """
        return self.SessionLocal()
    
    def initialize_schema(self) -> bool:
        """
        Create database tables if they don't exist.
        Does not drop existing tables - safe for production use.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create all tables from ORM models (only creates if they don't exist)
            Base.metadata.create_all(self.engine)
            from polyplexity_agent.logging import get_logger
            logger = get_logger(__name__)
            logger.info("database_schema_initialized")
            return True
        except Exception as e:
            from polyplexity_agent.logging import get_logger
            logger = get_logger(__name__)
            logger.error("database_schema_init_failed", error=str(e), exc_info=True)
            import traceback
            traceback.print_exc()
            return False
    
    def reset_database(self) -> bool:
        """
        Drop all tables and recreate schema from scratch.
        WARNING: This will delete all data! Use with caution.
        Only call this manually when you want a fresh start.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Drop all tables (including checkpoints table managed by LangGraph)
            with self.engine.connect() as conn:
                # Drop tables in order to handle foreign key constraints
                conn.execute(text("DROP TABLE IF EXISTS execution_traces CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS messages CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS threads CASCADE"))
                # Checkpoints table may not exist, so ignore errors
                try:
                    conn.execute(text("DROP TABLE IF EXISTS checkpoints CASCADE"))
                except Exception:
                    pass  # Table may not exist
                conn.commit()
            
            # Create all tables from ORM models
            Base.metadata.create_all(self.engine)
            from polyplexity_agent.logging import get_logger
            logger = get_logger(__name__)
            logger.info("database_reset_completed")
            return True
        except Exception as e:
            from polyplexity_agent.logging import get_logger
            logger = get_logger(__name__)
            logger.error("database_reset_failed", error=str(e), exc_info=True)
            import traceback
            traceback.print_exc()
            return False
    
    def save_thread_name(self, thread_id: str, name: str) -> None:
        """
        Save or update a thread name.
        
        Args:
            thread_id: The thread ID
            name: The thread name (should be 5 words or less)
        """
        session = self.get_session()
        try:
            thread = session.query(Thread).filter(Thread.thread_id == thread_id).first()
            if thread:
                thread.name = name
                thread.updated_at = datetime.now(timezone.utc)
            else:
                thread = Thread(thread_id=thread_id, name=name)
                session.add(thread)
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """
        Get a thread by ID.
        
        Args:
            thread_id: The thread ID
            
        Returns:
            Thread object or None if not found
        """
        session = self.get_session()
        try:
            return session.query(Thread).filter(Thread.thread_id == thread_id).first()
        finally:
            session.close()
    
    def get_thread_name(self, thread_id: str) -> Optional[str]:
        """
        Get the name for a thread.
        
        Args:
            thread_id: The thread ID
            
        Returns:
            Thread name if exists, None otherwise
        """
        thread = self.get_thread(thread_id)
        return thread.name if thread else None
    
    def save_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        message_index: Optional[int] = None
    ) -> str:
        """
        Save a message to the messages table.
        
        Args:
            thread_id: The thread ID this message belongs to
            role: Message role ('user' or 'assistant')
            content: Message content
            message_index: Optional index for ordering. If None, will be auto-incremented
            
        Returns:
            The UUID of the created message
        """
        if role not in ('user', 'assistant'):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")
        
        session = self.get_session()
        try:
            # Auto-increment message_index if not provided
            if message_index is None:
                max_index = session.query(Message.message_index).filter(
                    Message.thread_id == thread_id
                ).order_by(Message.message_index.desc()).first()
                message_index = (max_index[0] + 1) if max_index else 0
            
            message = Message(
                thread_id=thread_id,
                role=role,
                content=content,
                message_index=message_index
            )
            session.add(message)
            session.commit()
            return str(message.id)
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def save_execution_trace(
        self,
        message_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        timestamp: Optional[int] = None,
        event_index: Optional[int] = None
    ) -> str:
        """
        Save an execution trace event to the execution_traces table.
        
        Args:
            message_id: The UUID of the message this trace belongs to
            event_type: Type of event (e.g., 'node_call', 'reasoning', 'search')
            event_data: Event data as a dictionary (will be stored as JSON)
            timestamp: Optional timestamp in milliseconds. If None, uses current time
            event_index: Optional index for ordering. If None, will be auto-incremented
            
        Returns:
            The UUID of the created trace event
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000)  # Milliseconds
        
        session = self.get_session()
        try:
            # Auto-increment event_index if not provided
            if event_index is None:
                max_index = session.query(ExecutionTrace.event_index).filter(
                    ExecutionTrace.message_id == message_id
                ).order_by(ExecutionTrace.event_index.desc()).first()
                event_index = (max_index[0] + 1) if max_index else 0
            
            trace = ExecutionTrace(
                message_id=message_id,
                event_type=event_type,
                event_data=event_data,
                timestamp=timestamp,
                event_index=event_index
            )
            session.add(trace)
            session.commit()
            return str(trace.id)
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_message_traces(self, message_id: str) -> None:
        """
        Delete all execution trace events for a specific message.
        
        Args:
            message_id: The UUID of the message whose traces should be deleted
        """
        session = self.get_session()
        try:
            session.query(ExecutionTrace).filter(
                ExecutionTrace.message_id == message_id
            ).delete()
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a thread, ordered by message_index.
        
        Args:
            thread_id: The thread ID to retrieve messages for
            
        Returns:
            List of message dictionaries with keys: id, role, content, created_at, message_index
        """
        session = self.get_session()
        try:
            messages = session.query(Message).filter(
                Message.thread_id == thread_id
            ).order_by(Message.message_index.asc()).all()
            
            return [
                {
                    'id': str(msg.id),
                    'role': msg.role,
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat() if msg.created_at else None,
                    'message_index': msg.message_index
                }
                for msg in messages
            ]
        finally:
            session.close()
    
    def get_message_traces(self, message_id: str) -> List[Dict[str, Any]]:
        """
        Get all execution trace events for a message, ordered by event_index.
        
        Args:
            message_id: The message UUID to retrieve traces for
            
        Returns:
            List of trace event dictionaries with keys: id, event_type, event_data, timestamp, event_index
        """
        session = self.get_session()
        try:
            traces = session.query(ExecutionTrace).filter(
                ExecutionTrace.message_id == message_id
            ).order_by(ExecutionTrace.event_index.asc()).all()
            
            return [
                {
                    'id': str(trace.id),
                    'event_type': trace.event_type,
                    'event_data': trace.event_data or {},
                    'timestamp': trace.timestamp,
                    'event_index': trace.event_index
                }
                for trace in traces
            ]
        finally:
            session.close()
    
    def get_thread_messages_with_traces(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Get all messages for a thread with their execution traces attached.
        
        Args:
            thread_id: The thread ID to retrieve messages for
            
        Returns:
            List of message dictionaries with execution_trace attached to assistant messages
        """
        messages = self.get_thread_messages(thread_id)
        
        # Attach execution traces to assistant messages
        for msg in messages:
            if msg['role'] == 'assistant':
                traces = self.get_message_traces(msg['id'])
                # Convert traces to ExecutionTraceEvent format
                execution_trace = []
                for trace in traces:
                    execution_trace.append({
                        'type': trace['event_type'],
                        'node': trace['event_data'].get('node', ''),
                        'timestamp': trace['timestamp'],
                        'data': trace['event_data']
                    })
                msg['execution_trace'] = execution_trace if execution_trace else None
            else:
                msg['execution_trace'] = None
        
        return messages
    
    def get_last_message_for_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the last message for a thread.
        
        Args:
            thread_id: The thread ID
            
        Returns:
            Message dictionary or None if no messages exist
        """
        session = self.get_session()
        try:
            message = session.query(Message).filter(
                Message.thread_id == thread_id
            ).order_by(Message.message_index.desc()).first()
            
            if message:
                return {
                    'id': str(message.id),
                    'role': message.role,
                    'content': message.content,
                    'created_at': message.created_at.isoformat() if message.created_at else None,
                    'message_index': message.message_index
                }
            return None
        finally:
            session.close()
    
    def get_thread_message_count(self, thread_id: str) -> int:
        """
        Get the count of messages in a thread.
        
        Args:
            thread_id: The thread ID
        
        Returns:
            Number of messages in the thread
        """
        session = self.get_session()
        try:
            return session.query(Message).filter(Message.thread_id == thread_id).count()
        finally:
            session.close()
    
    def delete_thread(self, thread_id: str) -> None:
        """
        Delete a thread and all associated messages and execution traces.
        Uses CASCADE delete via foreign key relationships.
        
        Args:
            thread_id: The thread ID to delete
        """
        session = self.get_session()
        try:
            thread = session.query(Thread).filter(Thread.thread_id == thread_id).first()
            if thread:
                session.delete(thread)
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()


# Global instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """
    Get the global DatabaseManager instance.
    Creates it if it doesn't exist.
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

