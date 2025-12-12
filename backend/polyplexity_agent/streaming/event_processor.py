"""
Event processor for LangGraph stream events.

Processes events from LangGraph stream and ensures they're in standardized format.
Replaces auto-wrapping logic in entrypoint.py.
"""
from typing import Any, Dict, Iterator


def process_custom_events(mode: str, data: Any) -> Iterator[Dict[str, Any]]:
    """
    Process custom events from LangGraph stream.
    
    Ensures events are in envelope format and yields them one by one.
    
    Args:
        mode: Stream mode (should be "custom")
        data: Event data from LangGraph stream (may be single dict or list)
        
    Yields:
        Event dictionaries in standardized envelope format
    """
    if mode != "custom":
        return
    
    # Ensure data is iterable
    items = data if isinstance(data, list) else [data]
    
    for item in items:
        if not isinstance(item, dict):
            continue
        
        # Normalize to envelope format
        normalized = normalize_event(item)
        yield normalized


def process_update_events(mode: str, data: Any) -> Iterator[Dict[str, Any]]:
    """
    Process state update events from LangGraph stream.
    
    Converts state updates to envelope format.
    
    Args:
        mode: Stream mode (should be "updates")
        data: State update data from LangGraph stream (dict mapping node names to updates)
        
    Yields:
        Event dictionaries in standardized envelope format
    """
    if mode != "updates":
        return
    
    if not isinstance(data, dict):
        return
    
    for node_name, node_data in data.items():
        if isinstance(node_data, dict):
            # Create envelope for state update
            update_envelope = {
                "type": "state_update",
                "timestamp": int(__import__("time").time() * 1000),
                "node": node_name,
                "event": "state_update",
                "payload": node_data
            }
            
            # Determine specific event name
            if "final_report" in node_data:
                update_envelope["event"] = "final_report_update"
            elif "research_notes" in node_data:
                update_envelope["event"] = "research_notes_added"
            elif "iterations" in node_data:
                update_envelope["event"] = "iterations_incremented"
            
            yield update_envelope


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an event to envelope format.
    
    Handles events that may not already be in envelope format.
    This is a copy of the function from sse.py to avoid circular imports.
    
    Args:
        event: Event dictionary (may be in old format or envelope format)
        
    Returns:
        Event in standardized envelope format
    """
    # If already in envelope format, return as-is
    if all(key in event for key in ["type", "timestamp", "node", "event", "payload"]):
        return event
    
    # If event has type, event, and payload but missing timestamp/node, fill them in
    if "type" in event and "event" in event and "payload" in event:
        return {
            "type": event["type"],
            "timestamp": event.get("timestamp", int(__import__("time").time() * 1000)),
            "node": event.get("node", "unknown"),
            "event": event["event"],
            "payload": event["payload"]
        }
    
    # Handle old format: {"event": "...", ...}
    if "event" in event and "type" not in event:
        event_name = event["event"]
        
        # Extract node if present
        node = event.get("node", "unknown")
        
        # Create payload from all non-envelope fields
        payload = {k: v for k, v in event.items() if k not in ["event", "node"]}
        
        # Determine type from event name
        event_type = "custom"
        if event_name == "trace":
            event_type = "trace"
        elif event_name in ["thread_id", "thread_name"]:
            event_type = "system"
        
        return {
            "type": event_type,
            "timestamp": event.get("timestamp", int(__import__("time").time() * 1000)),
            "node": node,
            "event": event_name,
            "payload": payload
        }
    
    # Handle trace events in old format: {"type": "...", "node": "...", "data": {...}}
    if "type" in event and "data" in event and "payload" not in event:
        return {
            "type": event.get("type", "trace"),
            "timestamp": event.get("timestamp", int(__import__("time").time() * 1000)),
            "node": event.get("node", "unknown"),
            "event": event.get("type", "trace"),
            "payload": event.get("data", {})
        }
    
    # Default: wrap in envelope
    return {
        "type": "custom",
        "timestamp": int(__import__("time").time() * 1000),
        "node": event.get("node", "unknown"),
        "event": event.get("event", "unknown"),
        "payload": event
    }
