"""
Database configuration helper for PostgreSQL checkpointing.
Handles connection string creation and PostgresSaver initialization.
"""
import os
from typing import Optional

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

def get_postgres_connection_string() -> Optional[str]:
    """
    Get PostgreSQL connection string from environment variable.
    
    Returns:
        Connection string if POSTGRES_CONNECTION_STRING is set, None otherwise
    """
    # Use single connection string environment variable
    conn_string = os.getenv("POSTGRES_CONNECTION_STRING")
    return conn_string


# Global variable to keep context manager alive (prevents connection from closing)
_checkpointer_context = None

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
        print(f"✓ PostgresSaver checkpointer created successfully")
        print(f"  Checkpointer type: {type(checkpointer)}")
        print(f"  Has setup method: {hasattr(checkpointer, 'setup')}")
        # Setup will be called separately to ensure it's only called once
        return checkpointer
    except Exception as e:
        print(f"Warning: Failed to create PostgresSaver: {e}")
        # Don't print full connection string (contains password)
        print(f"Connection string format: postgresql://user:password@host:port/database")
        print("Make sure your POSTGRES_CONNECTION_STRING is correctly formatted.")
        print("Continuing without checkpointing...")
        _checkpointer_context = None
        return None


def is_checkpointing_available() -> bool:
    """
    Check if checkpointing is available (database configured).
    
    Returns:
        True if POSTGRES_CONNECTION_STRING is set, False otherwise
    """
    return os.getenv("POSTGRES_CONNECTION_STRING") is not None

