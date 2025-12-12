"""
Event serializers for standardized streaming envelope format.

All events are serialized into a common envelope format:
{
    "type": str,           # Event type (trace, custom, state_update, etc.)
    "timestamp": int,      # Unix timestamp in milliseconds
    "node": str,           # Node name that generated the event
    "event": str,          # Specific event name (e.g., "supervisor_decision", "node_call")
    "payload": dict        # Event-specific data
}
"""
import time
from typing import Any, Dict, Literal

# Trace event type definition (migrated from execution_trace.py)
TraceEventType = Literal["node_call", "reasoning", "search", "state_update", "custom"]


def create_trace_event(
    event_type: TraceEventType,
    node: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a structured execution trace event.
    
    Migrated from execution_trace.py.
    
    Args:
        event_type: Type of event (node_call, reasoning, search, state_update, custom)
        node: Name of the node that generated the event
        data: Event-specific data dictionary
        
    Returns:
        Structured trace event dictionary
    """
    return {
        "type": event_type,
        "node": node,
        "timestamp": int(time.time() * 1000),  # Unix timestamp in milliseconds
        "data": data
    }


def serialize_event(
    event_type: str,
    node: str,
    event: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a standardized event envelope.
    
    Args:
        event_type: Type of event (trace, custom, state_update, etc.)
        node: Name of the node that generated the event
        event: Specific event name (e.g., "supervisor_decision", "node_call")
        payload: Event-specific data dictionary
        
    Returns:
        Standardized event envelope dictionary
    """
    return {
        "type": event_type,
        "timestamp": int(time.time() * 1000),  # Unix timestamp in milliseconds
        "node": node,
        "event": event,
        "payload": payload
    }


def serialize_trace_event(
    trace_type: TraceEventType,
    node: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Serialize a trace event into envelope format.
    
    Uses execution_trace.create_trace_event() and wraps it in envelope format.
    
    Args:
        trace_type: Type of trace event (node_call, reasoning, search, state_update, custom)
        node: Name of the node that generated the event
        data: Event-specific data dictionary
        
    Returns:
        Standardized event envelope with trace event in payload
    """
    trace_event = create_trace_event(trace_type, node, data)
    
    # Extract event name from trace type or data
    event_name = trace_type
    if "event" in data:
        event_name = data["event"]
    
    return serialize_event(
        event_type="trace",
        node=node,
        event=event_name,
        payload=trace_event
    )


def serialize_custom_event(
    event_name: str,
    node: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Serialize a custom event into envelope format.
    
    Args:
        event_name: Name of the custom event (e.g., "supervisor_decision", "generated_queries")
        node: Name of the node that generated the event
        data: Event-specific data dictionary
        
    Returns:
        Standardized event envelope with custom event data in payload
    """
    return serialize_event(
        event_type="custom",
        node=node,
        event=event_name,
        payload=data
    )


def serialize_state_update(
    node: str,
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Serialize a state update event into envelope format.
    
    Args:
        node: Name of the node that generated the update
        update_data: State update data dictionary
        
    Returns:
        Standardized event envelope with state update data in payload
    """
    # Determine event name from update data
    event_name = "state_update"
    if "research_notes" in update_data:
        event_name = "research_notes_added"
    elif "iterations" in update_data:
        event_name = "iterations_incremented"
    elif "final_report" in update_data:
        event_name = "final_report_update"
    
    return serialize_event(
        event_type="state_update",
        node=node,
        event=event_name,
        payload=update_data
    )
