"""
Database migration utilities for creating message and execution trace tables.
These tables store UI-friendly conversation history separate from LangGraph state.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def get_postgres_connection_string() -> Optional[str]:
    """
    Get PostgreSQL connection string from environment variable.
    
    Returns:
        Connection string if POSTGRES_CONNECTION_STRING is set, None otherwise
    """
    return os.getenv("POSTGRES_CONNECTION_STRING")


def create_messages_table(conn) -> None:
    """
    Create the messages table if it doesn't exist.
    
    Args:
        conn: PostgreSQL connection object
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                message_index INTEGER NOT NULL
            );
        """)
        
        # Create indexes for performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_thread_id 
            ON messages(thread_id);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_thread_index 
            ON messages(thread_id, message_index);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_created_at 
            ON messages(created_at);
        """)
        
        conn.commit()


def create_execution_traces_table(conn) -> None:
    """
    Create the execution_traces table if it doesn't exist.
    
    Args:
        conn: PostgreSQL connection object
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS execution_traces (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                event_data JSONB,
                timestamp BIGINT NOT NULL,
                event_index INTEGER NOT NULL
            );
        """)
        
        # Create indexes for performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_traces_message_id 
            ON execution_traces(message_id);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_traces_message_index 
            ON execution_traces(message_id, event_index);
        """)
        
        conn.commit()


def create_threads_table(conn) -> None:
    """
    Create the threads table if it doesn't exist.
    Stores thread metadata including names.
    
    Args:
        conn: PostgreSQL connection object
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            );
        """)
        
        # Create indexes for performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_threads_created_at 
            ON threads(created_at);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_threads_updated_at 
            ON threads(updated_at);
        """)
        
        conn.commit()


def setup_message_tables() -> bool:
    """
    Set up message and execution_traces tables in PostgreSQL.
    
    Returns:
        True if setup successful, False otherwise
    """
    conn_string = get_postgres_connection_string()
    if not conn_string:
        print("Warning: POSTGRES_CONNECTION_STRING not set. Cannot create message tables.")
        return False
    
    try:
        import psycopg
    except ImportError:
        try:
            import psycopg2 as psycopg
        except ImportError:
            print("Warning: psycopg or psycopg2 not available. Cannot create message tables.")
            return False
    
    try:
        with psycopg.connect(conn_string) as conn:
            create_messages_table(conn)
            create_execution_traces_table(conn)
            create_threads_table(conn)
            print("✓ Message tables created successfully")
            return True
    except Exception as e:
        print(f"Error creating message tables: {e}")
        return False


if __name__ == "__main__":
    # Allow running as script to set up tables
    setup_message_tables()

