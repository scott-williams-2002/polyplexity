"""
Tests for secrets and database configuration.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from polyplexity_agent.config.secrets import (
    create_checkpointer,
    get_postgres_connection_string,
    is_checkpointing_available,
)


def test_get_postgres_connection_string_with_env_var():
    """
    Test get_postgres_connection_string when POSTGRES_CONNECTION_STRING is set.
    """
    test_conn_string = "postgresql://user:pass@localhost:5432/testdb"
    
    with patch.dict(os.environ, {"POSTGRES_CONNECTION_STRING": test_conn_string}):
        result = get_postgres_connection_string()
        assert result == test_conn_string


def test_get_postgres_connection_string_without_env_var():
    """
    Test get_postgres_connection_string when POSTGRES_CONNECTION_STRING is not set.
    """
    with patch.dict(os.environ, {}, clear=True):
        # Remove the key if it exists
        os.environ.pop("POSTGRES_CONNECTION_STRING", None)
        result = get_postgres_connection_string()
        assert result is None


def test_is_checkpointing_available_with_env_var():
    """
    Test is_checkpointing_available when POSTGRES_CONNECTION_STRING is set.
    """
    test_conn_string = "postgresql://user:pass@localhost:5432/testdb"
    
    with patch.dict(os.environ, {"POSTGRES_CONNECTION_STRING": test_conn_string}):
        result = is_checkpointing_available()
        assert result is True


def test_is_checkpointing_available_without_env_var():
    """
    Test is_checkpointing_available when POSTGRES_CONNECTION_STRING is not set.
    """
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("POSTGRES_CONNECTION_STRING", None)
        result = is_checkpointing_available()
        assert result is False


@patch("polyplexity_agent.config.secrets.PostgresSaver")
def test_create_checkpointer_success(mock_postgres_saver):
    """
    Test create_checkpointer when database is configured correctly.
    """
    test_conn_string = "postgresql://user:pass@localhost:5432/testdb"
    mock_checkpointer = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_checkpointer)
    mock_postgres_saver.from_conn_string = MagicMock(return_value=mock_context)
    
    with patch.dict(os.environ, {"POSTGRES_CONNECTION_STRING": test_conn_string}):
        result = create_checkpointer()
        
        assert result == mock_checkpointer
        mock_postgres_saver.from_conn_string.assert_called_once_with(test_conn_string)
        mock_context.__enter__.assert_called_once()


@patch("polyplexity_agent.config.secrets.PostgresSaver")
def test_create_checkpointer_with_psycopg_format(mock_postgres_saver):
    """
    Test create_checkpointer converts postgresql+psycopg:// to postgresql://.
    """
    test_conn_string = "postgresql+psycopg://user:pass@localhost:5432/testdb"
    expected_conn_string = "postgresql://user:pass@localhost:5432/testdb"
    mock_checkpointer = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_checkpointer)
    mock_postgres_saver.from_conn_string = MagicMock(return_value=mock_context)
    
    with patch.dict(os.environ, {"POSTGRES_CONNECTION_STRING": test_conn_string}):
        result = create_checkpointer()
        
        assert result == mock_checkpointer
        # Should be called with converted format
        mock_postgres_saver.from_conn_string.assert_called_once_with(expected_conn_string)


def test_create_checkpointer_no_env_var():
    """
    Test create_checkpointer when POSTGRES_CONNECTION_STRING is not set.
    """
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("POSTGRES_CONNECTION_STRING", None)
        result = create_checkpointer()
        assert result is None


@patch("polyplexity_agent.config.secrets.PostgresSaver")
def test_create_checkpointer_exception_handling(mock_postgres_saver):
    """
    Test create_checkpointer handles exceptions gracefully.
    """
    test_conn_string = "postgresql://user:pass@localhost:5432/testdb"
    mock_postgres_saver.from_conn_string = MagicMock(side_effect=Exception("Connection failed"))
    
    with patch.dict(os.environ, {"POSTGRES_CONNECTION_STRING": test_conn_string}):
        # Should not raise, but return None
        result = create_checkpointer()
        assert result is None
