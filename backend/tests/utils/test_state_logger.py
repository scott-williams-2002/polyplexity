"""
Tests for StateLogger utility.
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


def test_state_logger_initialization(temp_log_file):
    """Test StateLogger initializes correctly."""
    logger = StateLogger(temp_log_file)
    
    assert logger.log_file_path == temp_log_file
    assert logger.log_file is not None
    assert logger.log_file_path.exists()
    
    logger.close()


def test_state_logger_creates_directory():
    """Test StateLogger creates parent directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_path = Path(temp_dir) / "subdir" / "log.txt"
        
        logger = StateLogger(log_path)
        
        assert log_path.parent.exists()
        assert log_path.exists() or log_path.parent.exists()
        
        logger.close()


def test_state_logger_log_state(temp_log_file):
    """Test log_state writes state information to file."""
    logger = StateLogger(temp_log_file)
    
    test_state = {
        "user_request": "Test question",
        "iterations": 1,
        "research_notes": ["note1", "note2"],
    }
    
    logger.log_state(
        node_name="test_node",
        graph_type="MAIN_GRAPH",
        state=test_state,
        timing="BEFORE",
        iteration=1,
        additional_info="Test info"
    )
    
    logger.close()
    
    # Verify file was written
    content = temp_log_file.read_text()
    assert "test_node" in content
    assert "MAIN_GRAPH" in content
    assert "BEFORE" in content
    assert "Test question" in content
    assert "Test info" in content


def test_state_logger_format_state_value_string(temp_log_file):
    """Test _format_state_value formats strings correctly."""
    logger = StateLogger(temp_log_file)
    
    # Short string
    result = logger._format_state_value("short string")
    assert result == "short string"
    
    # Long string (should truncate)
    long_string = "a" * 3000
    result = logger._format_state_value(long_string)
    assert "[TRUNCATED" in result
    assert "3000" in result
    
    logger.close()


def test_state_logger_format_state_value_none(temp_log_file):
    """Test _format_state_value handles None."""
    logger = StateLogger(temp_log_file)
    
    result = logger._format_state_value(None)
    assert result == "None"
    
    logger.close()


def test_state_logger_format_state_value_list(temp_log_file):
    """Test _format_state_value formats lists correctly."""
    logger = StateLogger(temp_log_file)
    
    # Empty list
    result = logger._format_state_value([])
    assert result == "[]"
    
    # Short list
    short_list = ["item1", "item2", "item3"]
    result = logger._format_state_value(short_list)
    assert "item1" in result
    assert "item2" in result
    assert "item3" in result
    
    # Long list (should show preview)
    long_list = [f"item{i}" for i in range(10)]
    result = logger._format_state_value(long_list)
    assert "item0" in result
    assert "more items" in result or "7 more" in result
    
    logger.close()


def test_state_logger_format_state_value_dict(temp_log_file):
    """Test _format_state_value formats dictionaries correctly."""
    logger = StateLogger(temp_log_file)
    
    test_dict = {
        "key1": "value1",
        "key2": 123,
        "key3": ["nested", "list"],
    }
    
    result = logger._format_state_value(test_dict)
    assert "key1" in result
    assert "value1" in result
    assert "key2" in result
    assert "123" in result
    
    logger.close()


def test_state_logger_log_state_without_iteration(temp_log_file):
    """Test log_state works without iteration parameter."""
    logger = StateLogger(temp_log_file)
    
    logger.log_state(
        node_name="test_node",
        graph_type="SUBGRAPH",
        state={"key": "value"},
        timing="AFTER"
    )
    
    logger.close()
    
    content = temp_log_file.read_text()
    assert "test_node" in content
    assert "SUBGRAPH" in content
    assert "AFTER" in content
    assert "Iteration" not in content


def test_state_logger_log_state_without_additional_info(temp_log_file):
    """Test log_state works without additional_info parameter."""
    logger = StateLogger(temp_log_file)
    
    logger.log_state(
        node_name="test_node",
        graph_type="MAIN_GRAPH",
        state={"key": "value"},
        timing="INITIAL"
    )
    
    logger.close()
    
    content = temp_log_file.read_text()
    assert "test_node" in content
    assert "Additional Info" not in content


def test_state_logger_close(temp_log_file):
    """Test close method closes file properly."""
    logger = StateLogger(temp_log_file)
    
    assert logger.log_file is not None
    
    logger.close()
    
    assert logger.log_file is None


def test_state_logger_log_state_after_close(temp_log_file):
    """Test log_state does nothing after close is called."""
    logger = StateLogger(temp_log_file)
    logger.close()
    
    # Should not raise an error
    logger.log_state(
        node_name="test_node",
        graph_type="MAIN_GRAPH",
        state={"key": "value"},
        timing="BEFORE"
    )
    
    # File should not have been written to
    content = temp_log_file.read_text()
    assert "test_node" not in content


def test_state_logger_multiple_logs(temp_log_file):
    """Test StateLogger can handle multiple log entries."""
    logger = StateLogger(temp_log_file)
    
    logger.log_state(
        node_name="node1",
        graph_type="MAIN_GRAPH",
        state={"state1": "value1"},
        timing="BEFORE"
    )
    
    logger.log_state(
        node_name="node2",
        graph_type="MAIN_GRAPH",
        state={"state2": "value2"},
        timing="AFTER"
    )
    
    logger.close()
    
    content = temp_log_file.read_text()
    assert "node1" in content
    assert "node2" in content
    assert "value1" in content
    assert "value2" in content
