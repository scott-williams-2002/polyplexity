"""
Tests for utility helper functions.
"""
from unittest.mock import Mock, patch
from datetime import datetime

import pytest

from polyplexity_agent.utils.helpers import (
    format_date,
    create_llm_model,
    generate_thread_name,
    log_node_state,
    format_search_url_markdown,
    save_messages_and_trace,
    ensure_trace_completeness,
)


def test_format_date():
    """Test format_date returns correct date format."""
    result = format_date()
    
    # Verify format is MM DD YY
    assert len(result) == 8  # "MM DD YY" format
    parts = result.split()
    assert len(parts) == 3
    assert len(parts[0]) == 2  # Month
    assert len(parts[1]) == 2  # Day
    assert len(parts[2]) == 2  # Year
    
    # Verify it's a valid date format
    try:
        datetime.strptime(result, "%m %d %y")
    except ValueError:
        pytest.fail("format_date returned invalid date format")


@patch("polyplexity_agent.utils.helpers._settings")
def test_create_llm_model_defaults(mock_settings):
    """Test create_llm_model uses default settings."""
    mock_settings.model_name = "test-model"
    mock_settings.temperature = 0.5
    
    with patch("polyplexity_agent.utils.helpers.ChatGroq") as mock_chatgroq:
        mock_model = Mock()
        mock_chatgroq.return_value = mock_model
        
        result = create_llm_model()
        
        mock_chatgroq.assert_called_once_with(model="test-model", temperature=0.5)
        assert result == mock_model


@patch("polyplexity_agent.utils.helpers._settings")
def test_create_llm_model_with_overrides(mock_settings):
    """Test create_llm_model accepts model name and temperature overrides."""
    mock_settings.model_name = "default-model"
    mock_settings.temperature = 0.0
    
    with patch("polyplexity_agent.utils.helpers.ChatGroq") as mock_chatgroq:
        mock_model = Mock()
        mock_chatgroq.return_value = mock_model
        
        result = create_llm_model(model_name="custom-model", temperature=0.7)
        
        mock_chatgroq.assert_called_once_with(model="custom-model", temperature=0.7)
        assert result == mock_model


@patch("polyplexity_agent.logging.get_logger")
@patch("polyplexity_agent.utils.helpers._thread_name_model")
def test_generate_thread_name_success(mock_model, mock_get_logger):
    """Test generate_thread_name generates name from LLM response."""
    mock_response = Mock()
    mock_response.content = "Artificial Intelligence Research"
    mock_model.invoke.return_value = mock_response
    
    result = generate_thread_name("What is AI?")
    
    assert result == "Artificial Intelligence Research"
    mock_model.invoke.assert_called_once()


@patch("polyplexity_agent.logging.get_logger")
@patch("polyplexity_agent.utils.helpers._thread_name_model")
def test_generate_thread_name_removes_quotes(mock_model, mock_get_logger):
    """Test generate_thread_name removes surrounding quotes."""
    mock_response = Mock()
    mock_response.content = '"AI Research Topic"'
    mock_model.invoke.return_value = mock_response
    
    result = generate_thread_name("What is AI?")
    
    assert result == "AI Research Topic"
    assert not result.startswith('"')
    assert not result.endswith('"')


@patch("polyplexity_agent.logging.get_logger")
@patch("polyplexity_agent.utils.helpers._thread_name_model")
def test_generate_thread_name_truncates_long_names(mock_model, mock_get_logger):
    """Test generate_thread_name truncates names longer than 5 words."""
    mock_response = Mock()
    mock_response.content = "This is a very long thread name that exceeds five words"
    mock_model.invoke.return_value = mock_response
    
    result = generate_thread_name("Test query")
    
    words = result.split()
    assert len(words) <= 5
    assert result == "This is a very long"


@patch("polyplexity_agent.logging.get_logger")
@patch("polyplexity_agent.utils.helpers._thread_name_model")
def test_generate_thread_name_fallback_on_error(mock_model, mock_get_logger):
    """Test generate_thread_name falls back to truncated query on error."""
    mock_logger = Mock()
    mock_get_logger.return_value = mock_logger
    mock_model.invoke.side_effect = Exception("LLM error")
    
    result = generate_thread_name("What is artificial intelligence?")
    
    # Should fall back to first 5 words of query
    words = result.split()
    assert len(words) <= 5
    assert "What" in result or "artificial" in result
    mock_logger.warning.assert_called_once()


@patch("polyplexity_agent.logging.get_logger")
@patch("polyplexity_agent.utils.helpers._thread_name_model")
def test_generate_thread_name_fallback_on_empty(mock_model, mock_get_logger):
    """Test generate_thread_name falls back when LLM returns empty name."""
    mock_response = Mock()
    mock_response.content = ""
    mock_model.invoke.return_value = mock_response
    
    result = generate_thread_name("Test query with multiple words")
    
    # Should fall back to truncated query
    words = result.split()
    assert len(words) <= 5
    assert "Test" in result


def test_log_node_state_with_logger():
    """Test log_node_state calls logger when logger is provided."""
    mock_logger = Mock()
    test_state = {"key": "value"}
    
    log_node_state(
        logger=mock_logger,
        node_name="test_node",
        graph_type="MAIN_GRAPH",
        state=test_state,
        timing="BEFORE",
        iteration=1,
        additional_info="test info"
    )
    
    mock_logger.log_state.assert_called_once_with(
        node_name="test_node",
        graph_type="MAIN_GRAPH",
        state=test_state,
        timing="BEFORE",
        iteration=1,
        additional_info="test info"
    )


def test_log_node_state_without_logger():
    """Test log_node_state does nothing when logger is None."""
    # Should not raise an error
    log_node_state(
        logger=None,
        node_name="test_node",
        graph_type="MAIN_GRAPH",
        state={"key": "value"},
        timing="BEFORE"
    )


def test_format_search_url_markdown_standard_url():
    """Test format_search_url_markdown formats standard URL correctly."""
    url = "https://www.example.com/path/to/page"
    result = format_search_url_markdown(url)
    
    assert result == "[example.com](https://www.example.com/path/to/page)"


def test_format_search_url_markdown_without_www():
    """Test format_search_url_markdown handles URL without www."""
    url = "https://example.com/page"
    result = format_search_url_markdown(url)
    
    assert result == "[example.com](https://example.com/page)"


def test_format_search_url_markdown_invalid_url():
    """Test format_search_url_markdown handles invalid URL gracefully."""
    url = "not-a-valid-url"
    result = format_search_url_markdown(url)
    
    # Should fall back to wrapping invalid URL
    assert result == f"[{url}]({url})"


@patch("polyplexity_agent.utils.helpers.get_database_manager")
@patch("polyplexity_agent.logging.get_logger")
def test_save_messages_and_trace_success(mock_get_logger, mock_get_db_manager):
    """Test save_messages_and_trace saves messages and trace successfully."""
    mock_db_manager = Mock()
    mock_get_db_manager.return_value = mock_db_manager
    
    mock_db_manager.save_message.side_effect = ["user_msg_123", "assistant_msg_456"]
    
    execution_trace = [
        {"type": "node_call", "node": "test_node", "data": {"key": "value"}, "timestamp": 1234567890}
    ]
    
    result = save_messages_and_trace(
        thread_id="thread_123",
        user_request="Test request",
        final_report="Test report",
        execution_trace=execution_trace
    )
    
    assert result == "assistant_msg_456"
    assert mock_db_manager.save_message.call_count == 2
    mock_db_manager.save_execution_trace.assert_called_once()


@patch("polyplexity_agent.utils.helpers.get_database_manager")
@patch("polyplexity_agent.logging.get_logger")
def test_save_messages_and_trace_handles_error(mock_get_logger, mock_get_db_manager):
    """Test save_messages_and_trace handles database errors gracefully."""
    mock_logger = Mock()
    mock_get_logger.return_value = mock_logger
    mock_db_manager = Mock()
    mock_get_db_manager.return_value = mock_db_manager
    mock_db_manager.save_message.side_effect = Exception("Database error")
    
    result = save_messages_and_trace(
        thread_id="thread_123",
        user_request="Test request",
        final_report="Test report",
        execution_trace=[]
    )
    
    assert result is None
    mock_logger.warning.assert_called_once()


@patch("polyplexity_agent.utils.helpers.get_database_manager")
@patch("polyplexity_agent.logging.get_logger")
def test_ensure_trace_completeness_no_messages(mock_get_logger, mock_get_db_manager):
    """Test ensure_trace_completeness does nothing when no messages exist."""
    mock_db_manager = Mock()
    mock_get_db_manager.return_value = mock_db_manager
    mock_db_manager.get_thread_messages.return_value = []
    
    ensure_trace_completeness("thread_123", [])
    
    mock_db_manager.get_message_traces.assert_not_called()


@patch("polyplexity_agent.utils.helpers.get_database_manager")
@patch("polyplexity_agent.logging.get_logger")
def test_ensure_trace_completeness_complete_trace(mock_get_logger, mock_get_db_manager):
    """Test ensure_trace_completeness does nothing when trace is already complete."""
    mock_logger = Mock()
    mock_get_logger.return_value = mock_logger
    mock_db_manager = Mock()
    mock_get_db_manager.return_value = mock_db_manager
    
    mock_db_manager.get_thread_messages.return_value = [
        {"id": "msg_123", "role": "assistant"}
    ]
    mock_db_manager.get_message_traces.return_value = [
        {"event": "trace1"},
        {"event": "trace2"},
    ]
    
    expected_trace = [
        {"type": "node_call", "node": "node1", "data": {}, "timestamp": 1234567890},
        {"type": "node_call", "node": "node2", "data": {}, "timestamp": 1234567891},
    ]
    
    ensure_trace_completeness("thread_123", expected_trace)
    
    # Should not delete or update since trace is complete
    mock_db_manager.delete_message_traces.assert_not_called()


@patch("polyplexity_agent.utils.helpers.get_database_manager")
@patch("polyplexity_agent.logging.get_logger")
def test_ensure_trace_completeness_incomplete_trace(mock_get_logger, mock_get_db_manager):
    """Test ensure_trace_completeness updates trace when incomplete."""
    mock_logger = Mock()
    mock_get_logger.return_value = mock_logger
    mock_db_manager = Mock()
    mock_get_db_manager.return_value = mock_db_manager
    
    mock_db_manager.get_thread_messages.return_value = [
        {"id": "msg_123", "role": "assistant"}
    ]
    mock_db_manager.get_message_traces.return_value = [
        {"event": "trace1"},  # Only 1 trace, but expected has 2
    ]
    
    expected_trace = [
        {"type": "node_call", "node": "node1", "data": {}, "timestamp": 1234567890},
        {"type": "node_call", "node": "node2", "data": {}, "timestamp": 1234567891},
    ]
    
    ensure_trace_completeness("thread_123", expected_trace)
    
    # Should delete old traces and save new ones
    mock_db_manager.delete_message_traces.assert_called_once_with("msg_123")
    assert mock_db_manager.save_execution_trace.call_count == 2
