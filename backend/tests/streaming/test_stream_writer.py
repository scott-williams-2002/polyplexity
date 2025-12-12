"""
Tests for stream writer module.
"""
import pytest
from unittest.mock import Mock, patch

from polyplexity_agent.streaming.stream_writer import (
    stream_custom_event,
    stream_event,
    stream_state_update,
    stream_trace_event,
)


@patch("polyplexity_agent.streaming.stream_writer.get_stream_writer")
def test_stream_trace_event(mock_get_writer):
    """Test streaming trace events."""
    mock_writer = Mock()
    mock_get_writer.return_value = mock_writer
    
    stream_trace_event("node_call", "test_node", {"query": "test"})
    
    mock_get_writer.assert_called_once()
    mock_writer.assert_called_once()
    
    # Check that writer was called with envelope format
    call_args = mock_writer.call_args[0][0]
    assert call_args["type"] == "trace"
    assert call_args["node"] == "test_node"
    assert call_args["event"] == "node_call"
    assert "payload" in call_args


@patch("polyplexity_agent.streaming.stream_writer.get_stream_writer")
def test_stream_custom_event(mock_get_writer):
    """Test streaming custom events."""
    mock_writer = Mock()
    mock_get_writer.return_value = mock_writer
    
    stream_custom_event("supervisor_decision", "supervisor", {
        "decision": "research"
    })
    
    mock_get_writer.assert_called_once()
    mock_writer.assert_called_once()
    
    # Check that writer was called with envelope format
    call_args = mock_writer.call_args[0][0]
    assert call_args["type"] == "custom"
    assert call_args["node"] == "supervisor"
    assert call_args["event"] == "supervisor_decision"
    assert call_args["payload"] == {"decision": "research"}


@patch("polyplexity_agent.streaming.stream_writer.get_stream_writer")
def test_stream_state_update(mock_get_writer):
    """Test streaming state updates."""
    mock_writer = Mock()
    mock_get_writer.return_value = mock_writer
    
    stream_state_update("call_researcher", {
        "research_notes": ["Note 1"]
    })
    
    mock_get_writer.assert_called_once()
    mock_writer.assert_called_once()
    
    # Check that writer was called with envelope format
    call_args = mock_writer.call_args[0][0]
    assert call_args["type"] == "state_update"
    assert call_args["node"] == "call_researcher"
    assert "payload" in call_args


@patch("polyplexity_agent.streaming.stream_writer.get_stream_writer")
def test_stream_event_no_writer(mock_get_writer):
    """Test that streaming functions handle None writer gracefully."""
    mock_get_writer.return_value = None
    
    # Should not raise an error
    stream_trace_event("node_call", "test_node", {})
    stream_custom_event("test_event", "test_node", {})
    stream_state_update("test_node", {})


@patch("polyplexity_agent.streaming.stream_writer.get_stream_writer")
def test_stream_event_generic(mock_get_writer):
    """Test generic stream_event function."""
    mock_writer = Mock()
    mock_get_writer.return_value = mock_writer
    
    stream_event("custom", "test_node", "test_event", {"key": "value"})
    
    mock_get_writer.assert_called_once()
    mock_writer.assert_called_once()
    
    # Check that writer was called with envelope format
    call_args = mock_writer.call_args[0][0]
    assert call_args["type"] == "custom"
    assert call_args["node"] == "test_node"
    assert call_args["event"] == "test_event"
    assert call_args["payload"] == {"key": "value"}
