"""
Tests for event serializers module.
"""
import pytest
from polyplexity_agent.streaming.event_serializers import (
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
