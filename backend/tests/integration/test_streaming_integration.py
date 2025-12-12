"""
Integration tests for streaming functionality.

Tests SSE event streaming end-to-end.
"""
from unittest.mock import Mock, patch
from typing import Any, Dict, Iterator

import pytest

from polyplexity_agent.streaming import process_custom_events, process_update_events


@pytest.mark.integration
def test_process_custom_events_single():
    """Test processing single custom event."""
    event_data = {"event": "test_event", "data": "test"}
    events = list(process_custom_events("custom", event_data))

    assert len(events) > 0
    assert events[0]["event"] == "test_event"


@pytest.mark.integration
def test_process_custom_events_list():
    """Test processing list of custom events."""
    event_list = [
        {"event": "event1", "data": "data1"},
        {"event": "event2", "data": "data2"},
    ]
    events = list(process_custom_events("custom", event_list))

    assert len(events) == 2
    assert events[0]["event"] == "event1"
    assert events[1]["event"] == "event2"


@pytest.mark.integration
def test_process_update_events():
    """Test processing state update events."""
    update_data = {
        "supervisor": {"iterations": 1},
        "call_researcher": {"research_notes": ["Note 1"]},
    }
    events = list(process_update_events("updates", update_data))

    assert len(events) > 0


@pytest.mark.integration
def test_streaming_event_envelope_format():
    """Test that events are in correct envelope format."""
    event_data = {
        "type": "custom",
        "timestamp": 1234567890,
        "node": "supervisor",
        "event": "test_event",
        "payload": {"data": "test"},
    }
    events = list(process_custom_events("custom", event_data))

    assert len(events) > 0
    event = events[0]
    assert "type" in event or "event" in event
