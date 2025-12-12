"""
FastAPI application that wraps LangGraph agent with SSE streaming support.

Package Installation Requirement:
    The polyplexity_agent package must be installed in editable mode before running this application.
    
    Installation command:
        cd polyplexity_agent
        pip install -e .
    
    This allows main.py to import from the installed package:
        from polyplexity_agent import _checkpointer, main_graph, run_research_agent
"""
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import from installed polyplexity_agent package
# Package must be installed: cd polyplexity_agent && pip install -e .
from polyplexity_agent import _checkpointer, main_graph, run_research_agent
from polyplexity_agent.db_utils import get_database_manager
from polyplexity_agent.db_utils.db_setup import setup_checkpointer
from polyplexity_agent.streaming import create_sse_generator

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
        # Use SSE generator from streaming module
        # It handles all event formatting and completion/error events
        async for sse_line in create_sse_generator(run_research_agent(request.query, thread_id=thread_id)):
            yield sse_line
    
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
    List all conversation threads from the database.
    
    Returns:
        List of thread information including thread_id, last_message, and timestamp
    """
    try:
        db_manager = get_database_manager()
        
        # Get all threads from database
        session = db_manager.get_session()
        try:
            from polyplexity_agent.db_utils import Thread, Message
            
            # Get all threads with their messages
            threads_query = session.query(Thread).order_by(Thread.created_at.asc())
            thread_list = []
            
            for thread in threads_query.all():
                # Get last message for this thread
                last_msg = db_manager.get_last_message_for_thread(thread.thread_id)
                last_message = None
                if last_msg:
                    content = last_msg['content']
                    last_message = content[:100] + "..." if len(content) > 100 else content
                
                # Get message count
                message_count = db_manager.get_thread_message_count(thread.thread_id)
                
                # Format timestamp
                updated_at_str = None
                if thread.updated_at:
                    updated_at_str = thread.updated_at.isoformat()
                
                thread_list.append(ThreadInfo(
                    thread_id=thread.thread_id,
                    name=thread.name,
                    last_message=last_message or "No messages yet",
                    updated_at=updated_at_str,
                    message_count=message_count
                ))
            
            return thread_list
        finally:
            session.close()
        
    except Exception as e:
        print(f"Error listing threads: {e}")
        import traceback
        traceback.print_exc()
        return []


@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """
    Delete a conversation thread from the database.
    
    Args:
        thread_id: The thread ID to delete
        
    Returns:
        204 No Content on success
    """
    try:
        db_manager = get_database_manager()
        
        # Check if thread exists
        thread = db_manager.get_thread(thread_id)
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread '{thread_id}' not found"
            )
        
        # Delete thread (cascades to messages and execution_traces)
        db_manager.delete_thread(thread_id)
        
        # Also delete from LangGraph checkpointer if available
        if _checkpointer:
            try:
                _checkpointer.delete_thread(thread_id)
            except Exception as e:
                print(f"Warning: Failed to delete thread from checkpointer: {e}")
        
        return None  # FastAPI will return 204 No Content
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting thread {thread_id}: {e}")
        import traceback
        traceback.print_exc()
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
        # Try to get messages from database table first
        db_manager = get_database_manager()
        
        try:
            messages_from_table = db_manager.get_thread_messages_with_traces(thread_id)
            
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
    Initialize database schema on startup.
    Creates tables if they don't exist (does not drop existing data).
    Also ensures LangGraph checkpointer tables are created.
    """
    try:
        db_manager = get_database_manager()
        db_manager.initialize_schema()
    except Exception as e:
        print(f"Warning: Failed to initialize database schema on startup: {e}")
        traceback.print_exc()
        # Don't fail startup - database may already be set up
    
    # Setup checkpointer separately to ensure it's called even if schema init fails
    try:
        setup_checkpointer(_checkpointer)
    except Exception as e:
        print(f"Warning: Failed to setup checkpointer in startup event: {e}")
        traceback.print_exc()
        # Don't fail startup - checkpointer may have been set up during graph compilation

