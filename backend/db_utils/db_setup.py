"""
Database setup utilities for initializing LangGraph checkpointer tables.
"""
import traceback
from typing import Optional

from sqlalchemy import text

from .database_manager import get_database_manager


def _check_checkpoints_table_exists(session):
    """Check if checkpoints table exists in database."""
    result = session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'checkpoints'
        );
    """))
    return result.scalar()


def _create_checkpoints_table(session):
    """Create checkpoints table with required schema."""
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            parent_checkpoint_id TEXT,
            checkpoint JSONB NOT NULL,
            metadata JSONB,
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
        );
        CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_ns 
            ON checkpoints(thread_id, checkpoint_ns);
        CREATE INDEX IF NOT EXISTS idx_checkpoints_parent 
            ON checkpoints(parent_checkpoint_id);
    """))
    session.commit()
    print("[DEBUG] ✓ Created 'checkpoints' table manually")


def _verify_and_create_checkpoints_table():
    """Verify checkpoints table exists and create if missing."""
    db_manager = get_database_manager()
    session = db_manager.get_session()
    try:
        exists = _check_checkpoints_table_exists(session)
        if not exists:
            print("[DEBUG] ⚠️⚠️⚠️ 'checkpoints' table does NOT exist!")
            print("[DEBUG] Attempting to create checkpoints table manually...")
            _create_checkpoints_table(session)
        else:
            print("[DEBUG] ✓ 'checkpoints' table exists in database")
    finally:
        session.close()


def _log_select_sql_info(checkpointer):
    """Log SELECT_SQL information for debugging."""
    if hasattr(checkpointer, 'SELECT_SQL'):
        select_sql = str(checkpointer.SELECT_SQL)
        print(f"[DEBUG] SELECT_SQL (first 300 chars): {select_sql[:300]}")
        if 'checkpoints' in select_sql:
            print("[DEBUG] ⚠️ Checkpointer SQL references 'checkpoints' table")
        if 'checkpoint_blobs' in select_sql:
            print("[DEBUG] Checkpointer SQL references 'checkpoint_blobs' table")


def _log_upsert_sql_info(checkpointer):
    """Log UPSERT_CHECKPOINTS_SQL information for debugging."""
    if hasattr(checkpointer, 'UPSERT_CHECKPOINTS_SQL'):
        upsert_sql = str(checkpointer.UPSERT_CHECKPOINTS_SQL)
        print(f"[DEBUG] UPSERT_CHECKPOINTS_SQL (first 200 chars): {upsert_sql[:200]}")


def _log_checkpointer_sql_info(checkpointer):
    """Log checkpointer SQL information for debugging."""
    _log_select_sql_info(checkpointer)
    _log_upsert_sql_info(checkpointer)


def _log_checkpointer_debug_info(checkpointer):
    """Log checkpointer debug information."""
    print(f"[DEBUG] _checkpointer is: {checkpointer}")
    print(f"[DEBUG] Checkpointer type: {type(checkpointer)}")
    print(f"[DEBUG] Has setup method: {hasattr(checkpointer, 'setup')}")
    methods = [m for m in dir(checkpointer) if not m.startswith('_')]
    print(f"[DEBUG] Checkpointer methods: {methods}")


def _run_checkpointer_setup(checkpointer):
    """Run checkpointer setup and verify tables."""
    print("[DEBUG] Calling checkpointer.setup()...")
    checkpointer.setup()
    print("✓ LangGraph checkpointer tables initialized successfully")
    
    if hasattr(checkpointer, 'MIGRATIONS'):
        print(f"[DEBUG] Found {len(checkpointer.MIGRATIONS)} migrations")
    
    _log_checkpointer_sql_info(checkpointer)
    _verify_and_create_checkpoints_table()


def setup_checkpointer(checkpointer: Optional[object]):
    """
    Setup LangGraph checkpointer tables if checkpointer exists.
    
    Args:
        checkpointer: PostgresSaver checkpointer instance or None
    """
    print(f"[DEBUG] setup_checkpointer called")
    
    if not checkpointer:
        print("Warning: Checkpointer not available, skipping setup")
        return
    
    _log_checkpointer_debug_info(checkpointer)
    
    if not hasattr(checkpointer, "setup"):
        print("Warning: Checkpointer does not have setup method")
        return
    
    try:
        _run_checkpointer_setup(checkpointer)
    except Exception as e:
        print(f"Error: Failed to setup LangGraph checkpointer: {e}")
        traceback.print_exc()
        # Don't raise - allow startup to continue, but log the error

