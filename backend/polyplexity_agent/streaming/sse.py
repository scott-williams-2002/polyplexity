"""
SSE (Server-Sent Events) formatting and generator logic.

Handles formatting of standardized event envelopes into SSE format
and creating async generators for FastAPI StreamingResponse.
"""
import json
from typing import Any, AsyncIterator, Dict, Iterator

from polyplexity_agent.streaming.event_processor import normalize_event


def format_sse_event(event: Dict[str, Any]) -> str:
    """
    Format an event envelope as an SSE data line.
    
    Args:
        event: Event envelope dictionary (standardized format)
        
    Returns:
        SSE-formatted string: "data: {json}\n\n"
    """
    event_data = json.dumps(event)
    return f"data: {event_data}\n\n"


async def create_sse_generator(
    event_iterator: Iterator[tuple[str, Any]]
) -> AsyncIterator[str]:
    """
    Create an async SSE generator from a LangGraph event iterator.
    
    Processes events from run_research_agent() and formats them as SSE.
    Handles both custom events and state updates.
    
    Args:
        event_iterator: Iterator yielding (mode, data) tuples from LangGraph stream
        
    Yields:
        SSE-formatted strings ready for StreamingResponse
    """
    try:
        final_response = None
        
        for mode, data in event_iterator:
            if mode == "custom":
                # Custom events are already in envelope format
                # Ensure data is iterable (list) for uniform processing
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    # Normalize to envelope format if needed
                    normalized = normalize_event(item)
                    yield format_sse_event(normalized)
                    
                    # Capture final report when complete
                    if normalized.get("event") == "final_report_complete":
                        final_response = normalized.get("payload", {}).get("report", "")
            
            elif mode == "updates":
                # Emit state updates in envelope format
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
                        
                        yield format_sse_event(update_envelope)
                        
                        # Capture final report from state update
                        if "final_report" in node_data:
                            final_response = node_data.get("final_report", "")
        
        # Emit final completion event
        completion_event = format_completion_event(final_response or "")
        yield format_sse_event(completion_event)
        
    except Exception as e:
        # Stream error event before raising
        error_event = format_error_event(str(e))
        yield format_sse_event(error_event)
        raise


def format_completion_event(response: str) -> Dict[str, Any]:
    """
    Create a completion event envelope.
    
    Args:
        response: Final response content
        
    Returns:
        Completion event envelope
    """
    return {
        "type": "complete",
        "timestamp": int(__import__("time").time() * 1000),
        "node": "system",
        "event": "complete",
        "payload": {
            "response": response
        }
    }


def format_error_event(error: str) -> Dict[str, Any]:
    """
    Create an error event envelope.
    
    Args:
        error: Error message
        
    Returns:
        Error event envelope
    """
    return {
        "type": "error",
        "timestamp": int(__import__("time").time() * 1000),
        "node": "system",
        "event": "error",
        "payload": {
            "error": error
        }
    }


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an event to envelope format (for backward compatibility).
    
    Handles events that may not already be in envelope format.
    
    Args:
        event: Event dictionary (may be in old format or envelope format)
        
    Returns:
        Event in standardized envelope format
    """
    # If already in envelope format, return as-is
    if all(key in event for key in ["type", "timestamp", "node", "event", "payload"]):
        return event
    
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
