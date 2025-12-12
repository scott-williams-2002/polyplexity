"""
Database setup utilities for initializing LangGraph checkpointer tables.
"""
import traceback
from typing import Optional

from sqlalchemy import text

from polyplexity_agent.logging import get_logger

from .database_manager import get_database_manager

logger = get_logger(__name__)


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
    logger.debug("checkpoints_table_created")


def _verify_and_create_checkpoints_table():
    """Verify checkpoints table exists and create if missing."""
    db_manager = get_database_manager()
    session = db_manager.get_session()
    try:
        exists = _check_checkpoints_table_exists(session)
        if not exists:
            logger.debug("checkpoints_table_missing", message="Creating checkpoints table manually")
            _create_checkpoints_table(session)
        else:
            logger.debug("checkpoints_table_exists")
    finally:
        session.close()


def _log_select_sql_info(checkpointer):
    """Log SELECT_SQL information for debugging."""
    if hasattr(checkpointer, 'SELECT_SQL'):
        select_sql = str(checkpointer.SELECT_SQL)
        logger.debug("checkpointer_select_sql", sql_preview=select_sql[:300])
        if 'checkpoints' in select_sql:
            logger.debug("checkpointer_references_checkpoints_table")
        if 'checkpoint_blobs' in select_sql:
            logger.debug("checkpointer_references_checkpoint_blobs_table")


def _log_upsert_sql_info(checkpointer):
    """Log UPSERT_CHECKPOINTS_SQL information for debugging."""
    if hasattr(checkpointer, 'UPSERT_CHECKPOINTS_SQL'):
        upsert_sql = str(checkpointer.UPSERT_CHECKPOINTS_SQL)
        logger.debug("checkpointer_upsert_sql", sql_preview=upsert_sql[:200])


def _log_checkpointer_sql_info(checkpointer):
    """Log checkpointer SQL information for debugging."""
    _log_select_sql_info(checkpointer)
    _log_upsert_sql_info(checkpointer)


def _log_checkpointer_debug_info(checkpointer):
    """Log checkpointer debug information."""
    logger.debug("checkpointer_info", checkpointer=str(checkpointer), checkpointer_type=str(type(checkpointer)), has_setup=hasattr(checkpointer, 'setup'))
    methods = [m for m in dir(checkpointer) if not m.startswith('_')]
    logger.debug("checkpointer_methods", methods=methods)


def _run_checkpointer_setup(checkpointer):
    """Run checkpointer setup and verify tables."""
    logger.debug("calling_checkpointer_setup")
    checkpointer.setup()
    logger.info("checkpointer_tables_initialized")
    
    if hasattr(checkpointer, 'MIGRATIONS'):
        logger.debug("checkpointer_migrations_found", migration_count=len(checkpointer.MIGRATIONS))
    
    _log_checkpointer_sql_info(checkpointer)
    _verify_and_create_checkpoints_table()


def setup_checkpointer(checkpointer: Optional[object]):
    """
    Setup LangGraph checkpointer tables if checkpointer exists.
    
    Args:
        checkpointer: PostgresSaver checkpointer instance or None
    """
    logger.debug("setup_checkpointer_called")
    
    if not checkpointer:
        logger.warning("checkpointer_not_available")
        return
    
    _log_checkpointer_debug_info(checkpointer)
    
    if not hasattr(checkpointer, "setup"):
        logger.warning("checkpointer_no_setup_method")
        return
    
    try:
        _run_checkpointer_setup(checkpointer)
    except Exception as e:
        logger.error("checkpointer_setup_failed", error=str(e), exc_info=True)
        traceback.print_exc()
        # Don't raise - allow startup to continue, but log the error

