"""
Database configuration helper for PostgreSQL checkpointing.

This module provides backward compatibility by re-exporting functions
from config.secrets. The actual implementation has been moved to
config/secrets.py for better organization.
"""
from typing import Optional

from langgraph.checkpoint.postgres import PostgresSaver

from polyplexity_agent.config.secrets import (
    create_checkpointer as _create_checkpointer,
    get_postgres_connection_string as _get_postgres_connection_string,
    is_checkpointing_available as _is_checkpointing_available,
)


def get_postgres_connection_string() -> Optional[str]:
    """
    Get PostgreSQL connection string from environment variable.
    
    Returns:
        Connection string if POSTGRES_CONNECTION_STRING is set, None otherwise
    """
    return _get_postgres_connection_string()


def create_checkpointer() -> Optional[PostgresSaver]:
    """
    Create and initialize PostgresSaver checkpointer if database is configured.
    
    Returns:
        PostgresSaver instance if configured, None otherwise
    """
    return _create_checkpointer()


def is_checkpointing_available() -> bool:
    """
    Check if checkpointing is available (database configured).
    
    Returns:
        True if POSTGRES_CONNECTION_STRING is set, False otherwise
    """
    return _is_checkpointing_available()

