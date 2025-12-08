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

# Import research_agent from same directory
from research_agent import run_agent, agent_graph, _checkpointer
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
        - Custom events (thinking, tool_call, response, error)
        - State updates (conversation_history, final_response)
        - Final completion event
    """
    async def sse_generator():
        try:
            final_response = None
            
            # Run agent and stream events
            for mode, data in run_agent(request.query, thread_id=thread_id):
                if mode == "custom":
                    # Emit custom events (token, thinking, tool_call, response, error)
                    event_data = json.dumps(data)
                    yield f"data: {event_data}\n\n"
                    
                    # Capture tokens and accumulate for final response
                    if data.get("event") == "token":
                        if final_response is None:
                            final_response = ""
                        final_response += data.get("content", "")
                    elif data.get("event") == "response":
                        final_response = data.get("content", "")
                
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
                        
                        # Capture final response from state update
                        if isinstance(node_data, dict) and "final_response" in node_data:
                            final_response = node_data.get("final_response", "")
            
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
                        checkpoint->>'conversation_history' as conversation_history,
                        metadata->>'created_at' as created_at,
                        (SELECT COUNT(*) FROM checkpoints c2 WHERE c2.thread_id = c1.thread_id) as message_count
                    FROM checkpoints c1
                    WHERE thread_id IS NOT NULL
                    ORDER BY thread_id, metadata->>'created_at' DESC NULLS LAST
                """)
                
                rows = cur.fetchall()
                for row in rows:
                    thread_id, conversation_history, created_at, message_count = row
                    
                    # Extract last user message from conversation_history if available
                    last_message = None
                    if conversation_history:
                        try:
                            import json
                            history = json.loads(conversation_history) if isinstance(conversation_history, str) else conversation_history
                            if isinstance(history, list) and len(history) > 0:
                                # Find last user message
                                for msg in reversed(history):
                                    if isinstance(msg, str) and (msg.startswith("User: ") or msg.startswith("Human: ")):
                                        last_message = msg.replace("User: ", "").replace("Human: ", "")
                                        break
                        except:
                            pass
                    
                    threads.append(ThreadInfo(
                        thread_id=thread_id,
                        last_message=last_message or "No messages yet",
                        updated_at=created_at,
                        message_count=message_count or 0
                    ))
        
        # Sort by updated_at descending (most recent first)
        threads.sort(key=lambda x: x.updated_at or "", reverse=True)
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
            state = agent_graph.get_state(config)
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


@app.get("/threads/{thread_id}/history", response_model=List[Message])
async def get_thread_history(thread_id: str):
    """
    Get conversation history for a specific thread.
    
    Args:
        thread_id: The thread ID to retrieve history for
        
    Returns:
        List of messages with role and content
    """
    if not _checkpointer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkpointing not available. Database not configured."
        )
    
    try:
        # Get thread state using agent_graph
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = agent_graph.get_state(config)
        
        if not state_snapshot or not state_snapshot.values:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread '{thread_id}' not found"
            )
        
        # Extract conversation_history from state
        state_values = state_snapshot.values
        conversation_history = state_values.get("conversation_history", [])
        
        # Parse conversation_history (format: ["User: message", "Assistant: response", ...])
        messages = []
        for msg in conversation_history:
            if isinstance(msg, str):
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
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting thread history for {thread_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve thread history: {str(e)}"
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}

