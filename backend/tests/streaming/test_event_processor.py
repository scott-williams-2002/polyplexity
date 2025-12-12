"""
Tests for event processor module.
"""
import pytest
from polyplexity_agent.streaming.event_processor import (
    normalize_event,
    process_custom_events,
    process_update_events,
)


def test_process_custom_events_single():
    """Test processing single custom event."""
    data = {
        "type": "custom",
        "event": "supervisor_decision",
        "payload": {"decision": "research"}
    }
    
    events = list(process_custom_events("custom", data))
    
    assert len(events) == 1
    # Event should be normalized with all required fields
    assert events[0]["type"] == "custom"
    assert events[0]["event"] == "supervisor_decision"
    assert events[0]["payload"] == {"decision": "research"}
    assert "timestamp" in events[0]
    assert "node" in events[0]


def test_process_custom_events_list():
    """Test processing list of custom events."""
    data = [
        {"type": "custom", "event": "event1", "payload": {}},
        {"type": "custom", "event": "event2", "payload": {}}
    ]
    
    events = list(process_custom_events("custom", data))
    
    assert len(events) == 2
    # Events should be normalized with all required fields
    assert events[0]["type"] == "custom"
    assert events[0]["event"] == "event1"
    assert events[0]["payload"] == {}
    assert "timestamp" in events[0]
    assert "node" in events[0]
    
    assert events[1]["type"] == "custom"
    assert events[1]["event"] == "event2"
    assert events[1]["payload"] == {}
    assert "timestamp" in events[1]
    assert "node" in events[1]


def test_process_custom_events_wrong_mode():
    """Test that wrong mode returns empty iterator."""
    events = list(process_custom_events("updates", {}))
    assert len(events) == 0


def test_process_custom_events_non_dict():
    """Test that non-dict items are skipped."""
    data = [{"event": "test"}, "not_a_dict", {"event": "test2"}]
    
    events = list(process_custom_events("custom", data))
    
    assert len(events) == 2
    # Events should be normalized
    assert events[0]["event"] == "test"
    assert events[0]["type"] == "custom"
    assert "payload" in events[0]
    assert "timestamp" in events[0]
    assert "node" in events[0]
    
    assert events[1]["event"] == "test2"
    assert events[1]["type"] == "custom"
    assert "payload" in events[1]
    assert "timestamp" in events[1]
    assert "node" in events[1]


def test_process_update_events():
    """Test processing state update events."""
    data = {
        "supervisor": {"iterations": 5},
        "final_report": {"final_report": "Report content"}
    }
    
    events = list(process_update_events("updates", data))
    
    assert len(events) == 2
    
    # Check first event
    assert events[0]["type"] == "state_update"
    assert events[0]["node"] == "supervisor"
    assert events[0]["event"] == "iterations_incremented"
    assert events[0]["payload"] == {"iterations": 5}
    
    # Check second event
    assert events[1]["type"] == "state_update"
    assert events[1]["node"] == "final_report"
    assert events[1]["event"] == "final_report_update"
    assert events[1]["payload"] == {"final_report": "Report content"}


def test_process_update_events_wrong_mode():
    """Test that wrong mode returns empty iterator."""
    events = list(process_update_events("custom", {}))
    assert len(events) == 0


def test_process_update_events_non_dict():
    """Test that non-dict data returns empty iterator."""
    events = list(process_update_events("updates", "not_a_dict"))
    assert len(events) == 0


def test_normalize_event_envelope_format():
    """Test normalization of envelope format events."""
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
    """Test normalization of old format events."""
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
