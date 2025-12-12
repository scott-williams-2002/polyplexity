"""
Centralized streaming interface for nodes.

Nodes should use these functions instead of directly calling get_stream_writer().
All events are automatically serialized into the standardized envelope format.
"""
from typing import Any, Dict

from langgraph.config import get_stream_writer

from polyplexity_agent.streaming.event_serializers import (
    serialize_custom_event,
    serialize_state_update,
    serialize_trace_event,
)
from polyplexity_agent.streaming.event_serializers import TraceEventType


def stream_event(
    event_type: str,
    node: str,
    event: str,
    payload: Dict[str, Any]
) -> None:
    """
    Stream a generic event in standardized envelope format.
    
    Args:
        event_type: Type of event (trace, custom, state_update, etc.)
        node: Name of the node that generated the event
        event: Specific event name
        payload: Event-specific data dictionary
    """
    from polyplexity_agent.streaming.event_serializers import serialize_event
    
    writer = get_stream_writer()
    if writer:
        envelope = serialize_event(event_type, node, event, payload)
        writer(envelope)


def stream_trace_event(
    trace_type: TraceEventType,
    node: str,
    data: Dict[str, Any]
) -> None:
    """
    Stream a trace event in standardized envelope format.
    
    Args:
        trace_type: Type of trace event (node_call, reasoning, search, state_update, custom)
        node: Name of the node that generated the event
        data: Event-specific data dictionary
    """
    writer = get_stream_writer()
    if writer:
        envelope = serialize_trace_event(trace_type, node, data)
        writer(envelope)


def stream_custom_event(
    event_name: str,
    node: str,
    data: Dict[str, Any]
) -> None:
    """
    Stream a custom event in standardized envelope format.
    
    Args:
        event_name: Name of the custom event (e.g., "supervisor_decision", "generated_queries")
        node: Name of the node that generated the event
        data: Event-specific data dictionary
    """
    writer = get_stream_writer()
    if writer:
        envelope = serialize_custom_event(event_name, node, data)
        writer(envelope)


def stream_state_update(
    node: str,
    update_data: Dict[str, Any]
) -> None:
    """
    Stream a state update event in standardized envelope format.
    
    Args:
        node: Name of the node that generated the update
        update_data: State update data dictionary
    """
    writer = get_stream_writer()
    if writer:
        envelope = serialize_state_update(node, update_data)
        writer(envelope)
