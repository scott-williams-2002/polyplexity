"""
Database secrets and connection management.

Handles PostgreSQL connection string retrieval and PostgresSaver initialization.
Manages environment variable loading for database configuration.
"""
import os
from typing import Optional

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

from polyplexity_agent.logging import get_logger

load_dotenv()

logger = get_logger(__name__)

# Global variable to keep context manager alive (prevents connection from closing)
_checkpointer_context = None


def get_postgres_connection_string() -> Optional[str]:
    """
    Get PostgreSQL connection string from environment variable.
    
    Returns:
        Connection string if POSTGRES_CONNECTION_STRING is set, None otherwise
    """
    conn_string = os.getenv("POSTGRES_CONNECTION_STRING")
    return conn_string


def create_checkpointer() -> Optional[PostgresSaver]:
    """
    Create and initialize PostgresSaver checkpointer if database is configured.
    
    Returns:
        PostgresSaver instance if configured, None otherwise
    """
    global _checkpointer_context
    
    conn_string = get_postgres_connection_string()
    if not conn_string:
        return None
    
    try:
        # PostgresSaver uses psycopg directly, so it needs postgresql:// format
        # Convert postgresql+psycopg:// back to postgresql:// if needed
        if conn_string.startswith("postgresql+psycopg://"):
            conn_string = conn_string.replace("postgresql+psycopg://", "postgresql://", 1)
        
        # PostgresSaver.from_conn_string() returns a context manager
        # We need to keep the context manager alive and enter it
        _checkpointer_context = PostgresSaver.from_conn_string(conn_string)
        checkpointer = _checkpointer_context.__enter__()
        logger.info("checkpointer_created", checkpointer_type=str(type(checkpointer)), has_setup=hasattr(checkpointer, "setup"))
        # Setup will be called separately to ensure it's only called once
        return checkpointer
    except Exception as e:
        logger.warning("checkpointer_creation_failed", error=str(e))
        logger.info("checkpointer_connection_format_hint", format="postgresql://user:password@host:port/database")
        logger.info("continuing_without_checkpointing")
        _checkpointer_context = None
        return None


def is_checkpointing_available() -> bool:
    """
    Check if checkpointing is available (database configured).
    
    Returns:
        True if POSTGRES_CONNECTION_STRING is set, False otherwise
    """
    return os.getenv("POSTGRES_CONNECTION_STRING") is not None
