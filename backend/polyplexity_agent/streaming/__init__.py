"""Streaming module.

This module contains SSE and event handling functionality.
"""

from polyplexity_agent.streaming.event_processor import (
    normalize_event,
    process_custom_events,
    process_update_events,
)
from polyplexity_agent.streaming.event_serializers import (
    serialize_custom_event,
    serialize_event,
    serialize_state_update,
    serialize_trace_event,
)
from polyplexity_agent.streaming.sse import (
    create_sse_generator,
    format_completion_event,
    format_error_event,
    format_sse_event,
)
from polyplexity_agent.streaming.stream_writer import (
    stream_custom_event,
    stream_event,
    stream_state_update,
    stream_trace_event,
)

__all__ = [
    # Event serializers
    "serialize_event",
    "serialize_trace_event",
    "serialize_custom_event",
    "serialize_state_update",
    # Stream writers (for nodes)
    "stream_event",
    "stream_trace_event",
    "stream_custom_event",
    "stream_state_update",
    # SSE formatting
    "format_sse_event",
    "create_sse_generator",
    "format_completion_event",
    "format_error_event",
    # Event processing
    "process_custom_events",
    "process_update_events",
    "normalize_event",
]
