"""
Execution trace management for LangGraph agent system.
Handles creation, storage, and retrieval of execution trace events.
"""
import time
from typing import Any, Dict, List, Literal, Optional

TraceEventType = Literal["node_call", "reasoning", "search", "state_update", "custom"]


def create_trace_event(
    event_type: TraceEventType,
    node: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a structured execution trace event.
    
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

