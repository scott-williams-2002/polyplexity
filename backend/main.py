"""
FastAPI application that wraps LangGraph agent with SSE streaming support.
"""
import json
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import research agent from agent module
from agent import run_research_agent
from agent.research_agent import main_graph
from utils.db_config import get_postgres_connection_string

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


@app.post("/chat")
async def chat_agent(
    request: QueryRequest,
    thread_id: Optional[str] = Query(None, description="Optional thread ID for conversation continuity")
):
    """
    Chat endpoint that streams agent responses using Server-Sent Events (SSE).
    
    Args:
        request: Request body containing the user's query
        thread_id: Optional thread ID for maintaining conversation history
        
    Returns:
        StreamingResponse with SSE events containing:
        - Custom events (supervisor_decision, generated_queries, search_start, etc.)
        - State updates (research_notes, final_report, conversation_history)
        - Final completion event
    """
    async def sse_generator():
        try:
            final_response = None
            
            # Run research agent and stream events
            for mode, data in run_research_agent(request.query, thread_id=thread_id):
                if mode == "custom":
                    # Emit custom events (supervisor_decision, generated_queries, etc.)
                    event_data = json.dumps(data)
                    yield f"data: {event_data}\n\n"
                    
                    # Capture final report when complete
                    if data.get("event") == "final_report_complete":
                        final_response = data.get("report", "")
                
                elif mode == "updates":
                    # Emit state updates
                    for node_name, node_data in data.items():
                        update_data = {
                            "type": "update",
                            "node": node_name,
                            "data": node_data
                        }
                        event_data = json.dumps(update_data)
                        yield f"data: {event_data}\n\n"
                        
                        # Capture final report from state update
                        if isinstance(node_data, dict) and "final_report" in node_data:
                            final_response = node_data.get("final_report", "")
            
            # Emit final completion event
            completion_data = {
                "type": "complete",
                "response": final_response or ""
            }
            event_data = json.dumps(completion_data)
            yield f"data: {event_data}\n\n"
            
        except Exception as e:
            # Stream error event before raising
            error_data = {
                "event": "error",
                "error": str(e)
            }
            event_data = json.dumps(error_data)
            yield f"data: {event_data}\n\n"
            raise
    
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream"
    )


class ThreadInfo(BaseModel):
    thread_id: str
    name: Optional[str] = None
    last_message: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0


@app.get("/threads", response_model=List[ThreadInfo])
async def list_threads():
    """
    List all conversation threads from the checkpointer database.
    
    Returns:
        List of thread information including thread_id, last_message, and timestamp
    """
    # Import checkpointer from agent module
    from agent.research_agent import _checkpointer
    
    if not _checkpointer:
        return []
    
    try:
        # Query the database directly to get thread information
        conn_string = get_postgres_connection_string()
        if not conn_string:
            return []
        
        try:
            import psycopg
        except ImportError:
            # Fallback: try psycopg2
            try:
                import psycopg2 as psycopg
            except ImportError:
                print("Warning: psycopg or psycopg2 not available. Cannot list threads.")
                return []
        
        threads = []
        with psycopg.connect(conn_string) as conn:
            with conn.cursor() as cur:
                # Query checkpoint table for unique thread_ids with metadata
                # The checkpoint table structure: thread_id, checkpoint_ns, checkpoint_id, checkpoint, metadata
                cur.execute("""
                    SELECT DISTINCT ON (thread_id)
                        thread_id,
                        checkpoint->>'user_request' as user_request,
                        checkpoint->>'final_report' as final_report,
                        checkpoint->>'conversation_history' as conversation_history,
                        metadata->>'created_at' as created_at,
                        (SELECT COUNT(*) FROM checkpoints c2 WHERE c2.thread_id = c1.thread_id) as message_count
                    FROM checkpoints c1
                    WHERE thread_id IS NOT NULL
                    ORDER BY thread_id, metadata->>'created_at' DESC NULLS LAST
                """)
                
                rows = cur.fetchall()
                thread_ids = []
                thread_data = {}
                
                for row in rows:
                    thread_id, user_request, final_report, conversation_history, created_at, message_count = row
                    thread_ids.append(thread_id)
                    
                    # Extract last message - prefer user_request, then conversation_history, then final_report
                    last_message = None
                    if user_request:
                        last_message = user_request[:100] + "..." if len(user_request) > 100 else user_request
                    elif conversation_history:
                        try:
                            import json
                            history = json.loads(conversation_history) if isinstance(conversation_history, str) else conversation_history
                            if isinstance(history, list) and len(history) > 0:
                                # Find last user message
                                for msg in reversed(history):
                                    if isinstance(msg, str) and (msg.startswith("User: ") or msg.startswith("Human: ")):
                                        last_message = msg.replace("User: ", "").replace("Human: ", "")
                                        if len(last_message) > 100:
                                            last_message = last_message[:100] + "..."
                                        break
                        except:
                            pass
                    elif final_report:
                        last_message = final_report[:100] + "..." if len(final_report) > 100 else final_report
                    
                    thread_data[thread_id] = {
                        'last_message': last_message or "No messages yet",
                        'updated_at': created_at,
                        'message_count': message_count or 0
                    }
                
                # Get thread names and created_at from threads table
                thread_names = {}
                thread_created_at = {}
                if thread_ids:
                    placeholders = ','.join(['%s'] * len(thread_ids))
                    cur.execute(f"""
                        SELECT thread_id, name, created_at
                        FROM threads
                        WHERE thread_id IN ({placeholders})
                    """, tuple(thread_ids))
                    
                    name_rows = cur.fetchall()
                    for name_row in name_rows:
                        tid, name, created_at_from_threads = name_row
                        thread_names[tid] = name
                        thread_created_at[tid] = created_at_from_threads
                
                # Build thread info list with timestamps as datetime objects for sorting
                thread_list = []
                for thread_id in thread_ids:
                    data = thread_data[thread_id]
                    # Use created_at from threads table if available, otherwise use updated_at from checkpoints
                    sort_timestamp = thread_created_at.get(thread_id) or data['updated_at']
                    
                    # Normalize timestamp to datetime object for sorting
                    timestamp_dt = None
                    if sort_timestamp:
                        if hasattr(sort_timestamp, 'isoformat'):
                            # It's already a datetime object
                            timestamp_dt = sort_timestamp
                            # Ensure it's timezone-aware (use UTC if naive)
                            if timestamp_dt.tzinfo is None:
                                from datetime import timezone
                                timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
                        elif isinstance(sort_timestamp, str):
                            # Parse string to datetime
                            try:
                                # Handle ISO format strings
                                ts_str = sort_timestamp.replace('Z', '+00:00')
                                try:
                                    timestamp_dt = datetime.fromisoformat(ts_str)
                                except ValueError:
                                    # Try without timezone
                                    timestamp_dt = datetime.fromisoformat(sort_timestamp.split('+')[0].split('Z')[0])
                                    # Make it timezone-aware
                                    from datetime import timezone
                                    timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
                                # Ensure it's timezone-aware
                                if timestamp_dt.tzinfo is None:
                                    from datetime import timezone
                                    timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)
                            except Exception:
                                timestamp_dt = None
                    
                    thread_list.append({
                        'thread_id': thread_id,
                        'name': thread_names.get(thread_id),
                        'last_message': data['last_message'],
                        'updated_at_dt': timestamp_dt,
                        'message_count': data['message_count']
                    })
                
                # Sort by timestamp chronologically (oldest first)
                # Use a very old timezone-aware datetime as fallback for None values
                from datetime import timezone
                min_datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
                thread_list.sort(key=lambda x: x['updated_at_dt'] or min_datetime)
                
                # Convert datetime objects to ISO format strings for response
                for thread_data_item in thread_list:
                    updated_at_str = None
                    if thread_data_item['updated_at_dt']:
                        updated_at_str = thread_data_item['updated_at_dt'].isoformat()
                    
                    threads.append(ThreadInfo(
                        thread_id=thread_data_item['thread_id'],
                        name=thread_data_item['name'],
                        last_message=thread_data_item['last_message'],
                        updated_at=updated_at_str,
                        message_count=thread_data_item['message_count']
                    ))
        
        return threads
        
    except Exception as e:
        print(f"Error listing threads: {e}")
        # Fallback: return empty list
        return []


@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """
    Delete a conversation thread from the checkpointer database.
    
    Args:
        thread_id: The thread ID to delete
        
    Returns:
        204 No Content on success
    """
    # Import checkpointer from agent module
    from agent.research_agent import _checkpointer
    
    if not _checkpointer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkpointing not available. Database not configured."
        )
    
    try:
        # Use PostgresSaver's delete_thread method
        _checkpointer.delete_thread(thread_id)
        return None  # FastAPI will return 204 No Content
    except Exception as e:
        print(f"Error deleting thread {thread_id}: {e}")
        # Check if thread exists by trying to get its state
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = main_graph.get_state(config)
            if not state or not state.values:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Thread '{thread_id}' not found"
                )
        except HTTPException:
            raise
        except Exception:
            # Thread doesn't exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread '{thread_id}' not found"
            )
        # Other errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete thread: {str(e)}"
        )


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None
    execution_trace: Optional[List[dict]] = None  # Execution trace events


@app.get("/threads/{thread_id}/history", response_model=List[Message])
async def get_thread_history(thread_id: str):
    """
    Get conversation history for a specific thread.
    
    Retrieves messages from the separate messages table for UI-friendly access.
    Falls back to LangGraph state if table is empty (backward compatibility).
    
    Args:
        thread_id: The thread ID to retrieve history for
        
    Returns:
        List of messages with role, content, and execution_trace
    """
    try:
        # Try to get messages from separate table first
        from utils.message_store import get_thread_messages_with_traces
        
        try:
            messages_from_table = get_thread_messages_with_traces(thread_id)
            
            if messages_from_table:
                # Convert to Message format
                result = []
                for msg in messages_from_table:
                    # Convert execution_trace format if present
                    execution_trace = None
                    if msg.get("execution_trace"):
                        execution_trace = msg["execution_trace"]
                    
                    result.append(Message(
                        role=msg["role"],
                        content=msg["content"],
                        timestamp=msg.get("created_at"),
                        execution_trace=execution_trace
                    ))
                
                return result
        except Exception as e:
            print(f"Warning: Failed to get messages from table, falling back to state: {e}")
        
        # Fallback to LangGraph state (for backward compatibility or if table is empty)
        from agent.research_agent import _checkpointer
        
        if not _checkpointer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Checkpointing not available. Database not configured."
            )
        
        # Get thread state using main_graph
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = main_graph.get_state(config)
        
        if not state_snapshot or not state_snapshot.values:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread '{thread_id}' not found"
            )
        
        # Extract state values
        state_values = state_snapshot.values
        conversation_history = state_values.get("conversation_history", [])
        
        # Build messages from conversation_history (structured format)
        messages = []
        
        # Parse conversation_history - handle both new structured format and old string format
        for msg in conversation_history:
            if isinstance(msg, dict):
                # New structured format: {"role": "user"|"assistant", "content": str, "execution_trace": List[dict]|None}
                messages.append(Message(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    execution_trace=msg.get("execution_trace")
                ))
            elif isinstance(msg, str):
                # Old string format (backward compatibility): "User: message" or "Assistant: response"
                if msg.startswith("User: ") or msg.startswith("Human: "):
                    content = msg.replace("User: ", "").replace("Human: ", "")
                    messages.append(Message(
                        role="user",
                        content=content
                    ))
                elif msg.startswith("Assistant: ") or msg.startswith("AI: "):
                    content = msg.replace("Assistant: ", "").replace("AI: ", "")
                    messages.append(Message(
                        role="assistant",
                        content=content
                    ))
        
        # If conversation_history is empty, fall back to user_request and final_report
        if not messages:
            user_request = state_values.get("user_request", "")
            final_report = state_values.get("final_report", "")
            execution_trace = state_values.get("execution_trace", [])
            
            if user_request:
                messages.append(Message(
                    role="user",
                    content=user_request,
                    execution_trace=None
                ))
            
            if final_report:
                messages.append(Message(
                    role="assistant",
                    content=final_report,
                    execution_trace=execution_trace if execution_trace else None
                ))
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting thread history for {thread_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve thread history: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    """
    Initialize database tables on startup.
    Creates messages and execution_traces tables if they don't exist.
    """
    try:
        from utils.db_migrations import setup_message_tables
        setup_message_tables()
    except Exception as e:
        print(f"Warning: Failed to set up message tables on startup: {e}")
        # Don't fail startup if tables can't be created - they may already exist

