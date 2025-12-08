"""
Message and execution trace storage utilities.
Handles storing conversation history and execution traces in separate Postgres tables
for UI-friendly retrieval, separate from LangGraph state management.
"""
import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from .db_config import get_postgres_connection_string


def get_db_connection():
    """
    Get a PostgreSQL connection.
    
    Returns:
        PostgreSQL connection object
    """
    conn_string = get_postgres_connection_string()
    if not conn_string:
        raise ValueError("POSTGRES_CONNECTION_STRING not set")
    
    try:
        import psycopg
    except ImportError:
        try:
            import psycopg2 as psycopg
        except ImportError:
            raise ImportError("psycopg or psycopg2 required for message storage")
    
    return psycopg.connect(conn_string)


def save_message(
    thread_id: str,
    role: str,
    content: str,
    message_index: Optional[int] = None
) -> str:
    """
    Save a message to the messages table.
    
    Args:
        thread_id: The thread ID this message belongs to
        role: Message role ('user' or 'assistant')
        content: Message content
        message_index: Optional index for ordering. If None, will be auto-incremented
        
    Returns:
        The UUID of the created message
    """
    if role not in ('user', 'assistant'):
        raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")
    
    # Auto-increment message_index if not provided
    if message_index is None:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(MAX(message_index), -1) + 1
                    FROM messages
                    WHERE thread_id = %s
                """, (thread_id,))
                result = cur.fetchone()
                message_index = result[0] if result else 0
    
    message_id = str(uuid.uuid4())
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO messages (id, thread_id, role, content, message_index)
                VALUES (%s, %s, %s, %s, %s)
            """, (message_id, thread_id, role, content, message_index))
            conn.commit()
    
    return message_id


def save_execution_trace(
    message_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    timestamp: Optional[int] = None,
    event_index: Optional[int] = None
) -> str:
    """
    Save an execution trace event to the execution_traces table.
    
    Args:
        message_id: The UUID of the message this trace belongs to
        event_type: Type of event (e.g., 'node_call', 'reasoning', 'search')
        event_data: Event data as a dictionary (will be stored as JSONB)
        timestamp: Optional timestamp in milliseconds. If None, uses current time
        event_index: Optional index for ordering. If None, will be auto-incremented
        
    Returns:
        The UUID of the created trace event
    """
    if timestamp is None:
        import time
        timestamp = int(time.time() * 1000)  # Milliseconds
    
    # Auto-increment event_index if not provided
    if event_index is None:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COALESCE(MAX(event_index), -1) + 1
                    FROM execution_traces
                    WHERE message_id = %s
                """, (message_id,))
                result = cur.fetchone()
                event_index = result[0] if result else 0
    
    trace_id = str(uuid.uuid4())
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO execution_traces (id, message_id, event_type, event_data, timestamp, event_index)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                trace_id,
                message_id,
                event_type,
                json.dumps(event_data),
                timestamp,
                event_index
            ))
            conn.commit()
    
    return trace_id


def delete_message_traces(message_id: str):
    """
    Delete all execution trace events for a specific message.
    
    Args:
        message_id: The UUID of the message whose traces should be deleted
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM execution_traces WHERE message_id = %s",
                (message_id,)
            )
            conn.commit()


def get_thread_messages(thread_id: str) -> List[Dict[str, Any]]:
    """
    Get all messages for a thread, ordered by message_index.
    
    Args:
        thread_id: The thread ID to retrieve messages for
        
    Returns:
        List of message dictionaries with keys: id, role, content, created_at, message_index
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, role, content, created_at, message_index
                FROM messages
                WHERE thread_id = %s
                ORDER BY message_index ASC
            """, (thread_id,))
            
            rows = cur.fetchall()
            messages = []
            for row in rows:
                messages.append({
                    'id': str(row[0]),
                    'role': row[1],
                    'content': row[2],
                    'created_at': row[3].isoformat() if row[3] else None,
                    'message_index': row[4]
                })
            
            return messages


def get_message_traces(message_id: str) -> List[Dict[str, Any]]:
    """
    Get all execution trace events for a message, ordered by event_index.
    
    Args:
        message_id: The message UUID to retrieve traces for
        
    Returns:
        List of trace event dictionaries with keys: id, event_type, event_data, timestamp, event_index
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, event_type, event_data, timestamp, event_index
                FROM execution_traces
                WHERE message_id = %s
                ORDER BY event_index ASC
            """, (message_id,))
            
            rows = cur.fetchall()
            traces = []
            for row in rows:
                event_data = row[2]
                if isinstance(event_data, str):
                    try:
                        event_data = json.loads(event_data)
                    except json.JSONDecodeError:
                        event_data = {}
                elif event_data is None:
                    event_data = {}
                
                traces.append({
                    'id': str(row[0]),
                    'event_type': row[1],
                    'event_data': event_data,
                    'timestamp': row[3],
                    'event_index': row[4]
                })
            
            return traces


def get_thread_messages_with_traces(thread_id: str) -> List[Dict[str, Any]]:
    """
    Get all messages for a thread with their execution traces attached.
    
    Args:
        thread_id: The thread ID to retrieve messages for
        
    Returns:
        List of message dictionaries with execution_trace attached to assistant messages
    """
    messages = get_thread_messages(thread_id)
    
    # Attach execution traces to assistant messages
    for msg in messages:
        if msg['role'] == 'assistant':
            traces = get_message_traces(msg['id'])
            # Convert traces to ExecutionTraceEvent format
            execution_trace = []
            for trace in traces:
                execution_trace.append({
                    'type': trace['event_type'],
                    'node': trace['event_data'].get('node', ''),
                    'timestamp': trace['timestamp'],
                    'data': trace['event_data']
                })
            msg['execution_trace'] = execution_trace if execution_trace else None
        else:
            msg['execution_trace'] = None
    
    return messages


def get_last_message_for_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the last message for a thread.
    
    Args:
        thread_id: The thread ID
        
    Returns:
        Message dictionary or None if no messages exist
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, role, content, created_at, message_index
                FROM messages
                WHERE thread_id = %s
                ORDER BY message_index DESC
                LIMIT 1
            """, (thread_id,))
            
            row = cur.fetchone()
            if row:
                return {
                    'id': str(row[0]),
                    'role': row[1],
                    'content': row[2],
                    'created_at': row[3].isoformat() if row[3] else None,
                    'message_index': row[4]
                }
            return None


def get_thread_message_count(thread_id: str) -> int:
    """
    Get the count of messages in a thread.
    
    Args:
        thread_id: The thread ID
    
    Returns:
        Number of messages in the thread
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM messages
                WHERE thread_id = %s
            """, (thread_id,))
            
            result = cur.fetchone()
            return result[0] if result else 0


def save_thread_name(thread_id: str, name: str) -> None:
    """
    Save or update a thread name.
    
    Args:
        thread_id: The thread ID
        name: The thread name (should be 5 words or less)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO threads (thread_id, name, created_at, updated_at)
                VALUES (%s, %s, now(), now())
                ON CONFLICT (thread_id) 
                DO UPDATE SET name = %s, updated_at = now()
            """, (thread_id, name, name))
            conn.commit()


def get_thread_name(thread_id: str) -> Optional[str]:
    """
    Get the name for a thread.
    
    Args:
        thread_id: The thread ID
        
    Returns:
        Thread name if exists, None otherwise
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name
                FROM threads
                WHERE thread_id = %s
            """, (thread_id,))
            
            result = cur.fetchone()
            return result[0] if result else None

