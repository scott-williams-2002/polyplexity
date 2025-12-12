"""
Tests for SSE module.
"""
import json
import pytest
from polyplexity_agent.streaming.sse import (
    format_completion_event,
    format_error_event,
    format_sse_event,
    normalize_event,
)


def test_format_sse_event():
    """Test SSE event formatting."""
    event = {
        "type": "custom",
        "timestamp": 1234567890,
        "node": "test_node",
        "event": "test_event",
        "payload": {"key": "value"}
    }
    
    sse_line = format_sse_event(event)
    
    assert sse_line.startswith("data: ")
    assert sse_line.endswith("\n\n")
    
    # Parse the JSON to verify it's valid
    json_str = sse_line[6:-2]  # Remove "data: " and "\n\n"
    parsed = json.loads(json_str)
    assert parsed == event


def test_format_completion_event():
    """Test completion event formatting."""
    event = format_completion_event("Final response")
    
    assert event["type"] == "complete"
    assert event["node"] == "system"
    assert event["event"] == "complete"
    assert event["payload"]["response"] == "Final response"
    assert "timestamp" in event


def test_format_error_event():
    """Test error event formatting."""
    event = format_error_event("Error message")
    
    assert event["type"] == "error"
    assert event["node"] == "system"
    assert event["event"] == "error"
    assert event["payload"]["error"] == "Error message"
    assert "timestamp" in event


def test_normalize_event_already_envelope():
    """Test normalization of already-envelope events."""
    event = {
        "type": "custom",
        "timestamp": 1234567890,
        "node": "test_node",
        "event": "test_event",
        "payload": {"key": "value"}
    }
    
    normalized = normalize_event(event)
    assert normalized == event


def test_normalize_event_old_format():
    """Test normalization of old-format events."""
    event = {
        "event": "supervisor_decision",
        "decision": "research",
        "node": "supervisor"
    }
    
    normalized = normalize_event(event)
    
    assert normalized["type"] == "custom"
    assert normalized["node"] == "supervisor"
    assert normalized["event"] == "supervisor_decision"
    assert normalized["payload"] == {"decision": "research"}
    assert "timestamp" in normalized


def test_normalize_event_trace_format():
    """Test normalization of trace-format events."""
    event = {
        "type": "node_call",
        "node": "test_node",
        "data": {"query": "test"}
    }
    
    normalized = normalize_event(event)
    
    assert normalized["type"] == "node_call"
    assert normalized["node"] == "test_node"
    assert normalized["event"] == "node_call"
    assert normalized["payload"] == {"query": "test"}
    assert "timestamp" in normalized


def test_normalize_event_thread_id():
    """Test normalization of thread_id events."""
    event = {
        "event": "thread_id",
        "thread_id": "thread_123"
    }
    
    normalized = normalize_event(event)
    
    assert normalized["type"] == "system"
    assert normalized["event"] == "thread_id"
    assert normalized["payload"] == {"thread_id": "thread_123"}


def test_normalize_event_default():
    """Test normalization of unknown format events."""
    event = {
        "some_field": "some_value"
    }
    
    normalized = normalize_event(event)
    
    assert normalized["type"] == "custom"
    assert normalized["event"] == "unknown"
    assert normalized["payload"] == event
    assert "timestamp" in normalized
