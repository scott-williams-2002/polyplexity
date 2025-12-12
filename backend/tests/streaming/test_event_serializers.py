"""
Tests for event serializers module.
"""
import time

import pytest
from polyplexity_agent.streaming.event_serializers import (
    TraceEventType,
    create_trace_event,
    serialize_custom_event,
    serialize_event,
    serialize_state_update,
    serialize_trace_event,
)


def test_serialize_event():
    """Test basic event serialization."""
    event = serialize_event("custom", "test_node", "test_event", {"key": "value"})
    
    assert event["type"] == "custom"
    assert event["node"] == "test_node"
    assert event["event"] == "test_event"
    assert event["payload"] == {"key": "value"}
    assert "timestamp" in event
    assert isinstance(event["timestamp"], int)


def test_serialize_trace_event():
    """Test trace event serialization."""
    event = serialize_trace_event("node_call", "test_node", {"query": "test"})
    
    assert event["type"] == "trace"
    assert event["node"] == "test_node"
    assert event["event"] == "node_call"
    assert "payload" in event
    assert event["payload"]["type"] == "node_call"
    assert event["payload"]["node"] == "test_node"
    assert event["payload"]["data"] == {"query": "test"}


def test_serialize_custom_event():
    """Test custom event serialization."""
    event = serialize_custom_event("supervisor_decision", "supervisor", {
        "decision": "research",
        "topic": "AI trends"
    })
    
    assert event["type"] == "custom"
    assert event["node"] == "supervisor"
    assert event["event"] == "supervisor_decision"
    assert event["payload"] == {
        "decision": "research",
        "topic": "AI trends"
    }


def test_serialize_state_update():
    """Test state update serialization."""
    event = serialize_state_update("call_researcher", {
        "research_notes": ["Note 1", "Note 2"]
    })
    
    assert event["type"] == "state_update"
    assert event["node"] == "call_researcher"
    assert event["event"] == "research_notes_added"
    assert event["payload"] == {"research_notes": ["Note 1", "Note 2"]}


def test_serialize_state_update_iterations():
    """Test state update serialization for iterations."""
    event = serialize_state_update("supervisor", {
        "iterations": 5
    })
    
    assert event["type"] == "state_update"
    assert event["node"] == "supervisor"
    assert event["event"] == "iterations_incremented"
    assert event["payload"] == {"iterations": 5}


def test_serialize_state_update_final_report():
    """Test state update serialization for final report."""
    event = serialize_state_update("final_report", {
        "final_report": "Report content"
    })
    
    assert event["type"] == "state_update"
    assert event["node"] == "final_report"
    assert event["event"] == "final_report_update"
    assert event["payload"] == {"final_report": "Report content"}


def test_create_trace_event_basic():
    """Test basic trace event creation."""
    event = create_trace_event("node_call", "test_node", {"query": "test query"})
    
    assert event["type"] == "node_call"
    assert event["node"] == "test_node"
    assert event["data"] == {"query": "test query"}
    assert "timestamp" in event
    assert isinstance(event["timestamp"], int)


def test_create_trace_event_all_types():
    """Test all TraceEventType values."""
    event_types: list[TraceEventType] = ["node_call", "reasoning", "search", "state_update", "custom"]
    
    for event_type in event_types:
        event = create_trace_event(event_type, "test_node", {"key": "value"})
        assert event["type"] == event_type
        assert event["node"] == "test_node"
        assert event["data"] == {"key": "value"}


def test_create_trace_event_timestamp():
    """Verify timestamp is included and is milliseconds since epoch."""
    before = int(time.time() * 1000)
    event = create_trace_event("node_call", "test_node", {})
    after = int(time.time() * 1000)
    
    assert "timestamp" in event
    assert isinstance(event["timestamp"], int)
    assert before <= event["timestamp"] <= after
    # Verify it's in milliseconds (should be a large number)
    assert event["timestamp"] > 1000000000000  # Roughly year 2001 in milliseconds


def test_create_trace_event_data_preserved():
    """Test data dictionary is preserved correctly."""
    test_data = {
        "query": "test query",
        "results": ["result1", "result2"],
        "count": 2
    }
    
    event = create_trace_event("node_call", "test_node", test_data)
    
    assert event["data"] == test_data
    assert event["data"]["query"] == "test query"
    assert event["data"]["results"] == ["result1", "result2"]
    assert event["data"]["count"] == 2


def test_create_trace_event_node_name():
    """Test node name is included correctly."""
    event = create_trace_event("reasoning", "supervisor_node", {"reasoning": "test"})
    
    assert event["node"] == "supervisor_node"
    assert event["type"] == "reasoning"


def test_create_trace_event_nested_data():
    """Test nested data structures in data dict."""
    nested_data = {
        "outer": {
            "inner": {
                "value": 42,
                "list": [1, 2, 3]
            }
        },
        "array": [
            {"item": 1},
            {"item": 2}
        ]
    }
    
    event = create_trace_event("custom", "test_node", nested_data)
    
    assert event["data"] == nested_data
    assert event["data"]["outer"]["inner"]["value"] == 42
    assert event["data"]["outer"]["inner"]["list"] == [1, 2, 3]
    assert len(event["data"]["array"]) == 2
    assert event["data"]["array"][0]["item"] == 1
