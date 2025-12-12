"""
Tests for state_manager module.
"""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.utils.state_logger import StateLogger


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


def test_set_state_logger(temp_log_file):
    """Test setting and getting state logger."""
    from polyplexity_agent.utils import state_manager
    
    # Clear any existing logger
    state_manager.set_state_logger(None)
    
    # Create a new logger
    logger = StateLogger(temp_log_file)
    state_manager.set_state_logger(logger)
    
    # Verify it was set
    assert state_manager._state_logger is logger
    
    # Cleanup
    logger.close()
    state_manager.set_state_logger(None)


def test_set_state_logger_none(temp_log_file):
    """Test clearing state logger (set to None)."""
    from polyplexity_agent.utils import state_manager
    
    # Set a logger first
    logger = StateLogger(temp_log_file)
    state_manager.set_state_logger(logger)
    assert state_manager._state_logger is logger
    
    # Clear it
    state_manager.set_state_logger(None)
    assert state_manager._state_logger is None
    
    # Cleanup
    logger.close()


def test_ensure_checkpointer_setup_success():
    """Test successful checkpointer setup."""
    from polyplexity_agent.utils import state_manager
    
    # Create a mock checkpointer with setup method
    mock_checkpointer = Mock()
    mock_checkpointer.setup = Mock()
    
    # Reset the setup flag
    state_manager._checkpointer_setup_done = False
    
    # Call ensure_checkpointer_setup
    result = state_manager.ensure_checkpointer_setup(mock_checkpointer)
    
    # Verify setup was called
    mock_checkpointer.setup.assert_called_once()
    assert result is mock_checkpointer
    assert state_manager._checkpointer_setup_done is True


def test_ensure_checkpointer_setup_no_setup_method():
    """Test checkpointer without setup method."""
    from polyplexity_agent.utils import state_manager
    
    # Create a mock checkpointer without setup method
    mock_checkpointer = Mock(spec=[])  # No methods
    
    # Reset the setup flag
    state_manager._checkpointer_setup_done = False
    
    # Call ensure_checkpointer_setup
    with patch('polyplexity_agent.utils.state_manager.logger') as mock_logger:
        result = state_manager.ensure_checkpointer_setup(mock_checkpointer)
    
    # Verify warning was logged
    mock_logger.warning.assert_called_once()
    assert result is mock_checkpointer
    assert state_manager._checkpointer_setup_done is True


def test_ensure_checkpointer_setup_failure():
    """Test checkpointer setup failure handling."""
    from polyplexity_agent.utils import state_manager
    
    # Create a mock checkpointer that raises an exception
    mock_checkpointer = Mock()
    mock_checkpointer.setup = Mock(side_effect=Exception("Setup failed"))
    
    # Reset the setup flag
    state_manager._checkpointer_setup_done = False
    
    # Call ensure_checkpointer_setup
    with patch('polyplexity_agent.utils.state_manager.logger') as mock_logger:
        result = state_manager.ensure_checkpointer_setup(mock_checkpointer)
    
    # Verify error was logged
    mock_logger.error.assert_called_once()
    assert result is None
    assert state_manager._checkpointer_setup_done is True


def test_ensure_checkpointer_setup_none():
    """Test with None checkpointer."""
    from polyplexity_agent.utils import state_manager
    
    # Reset the setup flag
    state_manager._checkpointer_setup_done = False
    
    # Call ensure_checkpointer_setup with None
    result = state_manager.ensure_checkpointer_setup(None)
    
    # Should return None
    assert result is None


def test_main_graph_lazy_init():
    """Test main_graph lazy initialization."""
    from polyplexity_agent.utils import state_manager
    
    # Reset main_graph
    state_manager._main_graph = None
    
    # Mock create_agent_graph to avoid heavy compilation
    mock_graph = Mock()
    with patch('polyplexity_agent.graphs.agent_graph.create_agent_graph') as mock_create:
        mock_create.return_value = mock_graph
        
        # Access main_graph (triggers lazy init)
        graph = state_manager.main_graph
        
        # Verify graph was created
        assert graph is mock_graph
        mock_create.assert_called_once()


def test_main_graph_caching():
    """Test main_graph is cached after first access."""
    from polyplexity_agent.utils import state_manager
    
    # Reset main_graph
    state_manager._main_graph = None
    
    # Mock create_agent_graph
    mock_graph = Mock()
    with patch('polyplexity_agent.graphs.agent_graph.create_agent_graph') as mock_create:
        mock_create.return_value = mock_graph
        
        # Access main_graph twice
        graph1 = state_manager.main_graph
        graph2 = state_manager.main_graph
        
        # Verify graph is the same instance
        assert graph1 is graph2
        assert graph1 is mock_graph
        # Should only be created once
        assert mock_create.call_count == 1


def test_state_manager_imports():
    """Test all exports are accessible."""
    from polyplexity_agent.utils.state_manager import (
        _checkpointer,
        _state_logger,
        ensure_checkpointer_setup,
        set_state_logger,
    )
    
    # Verify imports work
    assert _checkpointer is not None or _checkpointer is None  # Can be None
    assert _state_logger is not None or _state_logger is None  # Can be None
    assert callable(ensure_checkpointer_setup)
    assert callable(set_state_logger)
