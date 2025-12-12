"""
Performance tests for streaming functionality.

Measures event streaming throughput.
"""
import time

import pytest

from polyplexity_agent.streaming import process_custom_events


@pytest.mark.slow
@pytest.mark.performance
def test_custom_event_processing_throughput():
    """Test that custom events can be processed quickly."""
    event_data = {"event": "test_event", "data": "test" * 100}

    start_time = time.time()
    events = list(process_custom_events("custom", event_data))
    end_time = time.time()

    assert len(events) > 0
    assert (end_time - start_time) < 0.1


@pytest.mark.slow
@pytest.mark.performance
def test_batch_event_processing_throughput():
    """Test processing multiple events in batch."""
    event_list = [{"event": f"event_{i}", "data": f"data_{i}"} for i in range(100)]

    start_time = time.time()
    events = list(process_custom_events("custom", event_list))
    end_time = time.time()

    assert len(events) == 100
    assert (end_time - start_time) < 1.0
