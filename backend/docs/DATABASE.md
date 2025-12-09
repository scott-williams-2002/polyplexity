# Database Architecture and Usage Guide

This document explains the database architecture, setup process, common pitfalls, and best practices for working with the Polyplexity backend database.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Tables](#database-tables)
3. [Setup and Initialization](#setup-and-initialization)
4. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Hybrid Persistence System

We use a **hybrid persistence approach** combining two layers:

**Layer 1: LangGraph Checkpointer (PostgresSaver)**
- Stores agent state: `research_notes`, `iterations`, `conversation_history`, `final_report`
- Used by LangGraph for graph execution and state management
- Tables: `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`
- Managed by LangGraph's `PostgresSaver` class

**Layer 2: Custom Message Store (PostgreSQL Tables)**
- `threads` table: Thread metadata including generated names
- `messages` table: User and assistant messages with `thread_id`, `role`, `content`, `message_index`
- `execution_traces` table: Execution trace events linked to messages via `message_id`
- Optimized for UI: Simple queries, fast retrieval, proper ordering

### Why Hybrid?

- **LangGraph checkpointer**: Required for graph state persistence and checkpointing during execution
- **Custom tables**: Optimized for UI queries, easier to query, better performance for message history
- **Separation of concerns**: Agent state vs. UI-friendly data structures

---

## Database Tables

### LangGraph Checkpointer Tables

These tables are created and managed by LangGraph's `PostgresSaver.setup()` method:

#### `checkpoints`
- **Purpose**: Stores checkpoint snapshots of agent state
- **Key Columns**:
  - `thread_id` (TEXT): Conversation thread identifier
  - `checkpoint_ns` (TEXT): Checkpoint namespace (default: '')
  - `checkpoint_id` (TEXT): Unique checkpoint identifier
  - `parent_checkpoint_id` (TEXT): Parent checkpoint for state lineage
  - `checkpoint` (JSONB): Full state snapshot
  - `metadata` (JSONB): Additional metadata
- **Primary Key**: `(thread_id, checkpoint_ns, checkpoint_id)`
- **Indexes**: `idx_checkpoints_thread_ns`, `idx_checkpoints_parent`

#### `checkpoint_blobs`
- **Purpose**: Stores large binary data associated with checkpoints
- **Managed by**: LangGraph internally

#### `checkpoint_writes`
- **Purpose**: Tracks checkpoint write operations
- **Managed by**: LangGraph internally

#### `checkpoint_migrations`
- **Purpose**: Tracks database schema migrations
- **Managed by**: LangGraph internally

### Custom Application Tables

These tables are created by `DatabaseManager.initialize_schema()`:

#### `threads`
- **Purpose**: Conversation thread metadata
- **Key Columns**:
  - `thread_id` (TEXT, PK): Unique thread identifier
  - `name` (TEXT): Human-readable thread name (5 words or less)
  - `created_at` (TIMESTAMP): Thread creation timestamp
  - `updated_at` (TIMESTAMP): Last update timestamp
- **Indexes**: `idx_threads_created_at`, `idx_threads_updated_at`

#### `messages`
- **Purpose**: User and assistant messages
- **Key Columns**:
  - `id` (UUID, PK): Unique message identifier
  - `thread_id` (TEXT, FK): References `threads.thread_id`
  - `role` (TEXT): 'user' or 'assistant'
  - `content` (TEXT): Message content
  - `created_at` (TIMESTAMP): Message creation timestamp
  - `message_index` (INTEGER): Order index within thread
- **Indexes**: `idx_messages_thread_id`, `idx_messages_thread_index`, `idx_messages_created_at`
- **Relationships**: Cascade delete with threads

#### `execution_traces`
- **Purpose**: Agent execution trace events
- **Key Columns**:
  - `id` (UUID, PK): Unique trace event identifier
  - `message_id` (UUID, FK): References `messages.id`
  - `event_type` (TEXT): Type of event ('node_call', 'reasoning', 'search', 'state_update', 'custom')
  - `event_data` (JSONB): Event-specific data
  - `timestamp` (BIGINT): Timestamp in milliseconds since epoch
  - `event_index` (INTEGER): Order index within message
- **Indexes**: `idx_execution_traces_message_id`, `idx_execution_traces_message_index`, `idx_execution_traces_timestamp`
- **Relationships**: Cascade delete with messages

---

## Setup and Initialization

### Initial Setup

1. **Set Environment Variable**:
   ```bash
   export POSTGRES_CONNECTION_STRING="postgresql://user:password@host:port/database"
   ```

2. **Database Schema Initialization**:
   The database schema is automatically initialized on server startup via the `startup_event()` function in `main.py`:
   ```python
   @app.on_event("startup")
   async def startup_event():
       db_manager = get_database_manager()
       db_manager.initialize_schema()  # Creates custom tables
       setup_checkpointer(_checkpointer)  # Creates LangGraph tables
   ```

### Manual Setup

If you need to manually initialize the database:

```python
from db_utils import get_database_manager
from db_utils.db_setup import setup_checkpointer
from agent import _checkpointer

# Initialize custom tables
db_manager = get_database_manager()
db_manager.initialize_schema()

# Initialize LangGraph checkpointer tables
setup_checkpointer(_checkpointer)
```

### Database Reset (Development Only)

⚠️ **WARNING**: This will delete all data!

```python
from db_utils import get_database_manager

db_manager = get_database_manager()
db_manager.reset_database()  # Drops all tables and recreates
```

---

## Common Pitfalls and Solutions

### Pitfall 1: Missing `checkpoints` Table

**Symptom**: 
```
psycopg.errors.UndefinedTable: relation "checkpoints" does not exist
LINE 26: from checkpoints WHERE thread_id = $1 AND checkpoint_ns = $2...
```

**Root Cause**: 
LangGraph's `PostgresSaver.setup()` method was called but didn't create the `checkpoints` table. This can happen due to:
- Version mismatches between `langgraph-checkpoint` and `langgraph-checkpoint-postgres`
- Setup() method failing silently
- Incomplete migration execution

**Solution**: 
The `db_setup.py` script automatically detects and creates the missing `checkpoints` table:
```python
# In db_utils/db_setup.py
def _verify_and_create_checkpoints_table():
    # Checks if table exists, creates if missing
```

**Prevention**: 
- Always call `setup_checkpointer(_checkpointer)` during startup
- Ensure both `langgraph-checkpoint` and `langgraph-checkpoint-postgres` are installed
- Check startup logs for "[DEBUG] ✓ 'checkpoints' table exists in database"

### Pitfall 2: Connection String Format Mismatch

**Symptom**: 
```
Warning: Failed to create PostgresSaver: ...
```

**Root Cause**: 
- SQLAlchemy uses `postgresql+psycopg://` format
- PostgresSaver uses `postgresql://` format
- Connection string conversion issues

**Solution**: 
The `db_config.py` automatically handles conversion:
```python
# Converts postgresql+psycopg:// back to postgresql:// for PostgresSaver
if conn_string.startswith("postgresql+psycopg://"):
    conn_string = conn_string.replace("postgresql+psycopg://", "postgresql://", 1)
```

**Prevention**: 
- Always use `postgresql://` format in `POSTGRES_CONNECTION_STRING`
- Let the code handle format conversion automatically

### Pitfall 3: Checkpointer Not Initialized

**Symptom**: 
```
Warning: Checkpointer not available, skipping setup
```

**Root Cause**: 
- `POSTGRES_CONNECTION_STRING` environment variable not set
- Database connection failed
- PostgresSaver creation failed

**Solution**: 
1. Verify `POSTGRES_CONNECTION_STRING` is set
2. Check database connectivity
3. Review startup logs for PostgresSaver creation errors

**Prevention**: 
- Always set `POSTGRES_CONNECTION_STRING` before starting the server
- Use connection pooling and error handling

### Pitfall 4: Table Creation Order Issues

**Symptom**: 
```
Foreign key constraint violations during table creation
```

**Root Cause**: 
- Tables created in wrong order
- Foreign key dependencies not respected

**Solution**: 
`DatabaseManager.initialize_schema()` uses SQLAlchemy's `Base.metadata.create_all()` which handles dependencies automatically.

**Prevention**: 
- Always use `initialize_schema()` instead of manual table creation
- Let SQLAlchemy handle dependency resolution

### Pitfall 5: Execution Trace Incomplete Persistence

**Symptom**: 
- Execution traces missing events
- Only `final_report` events visible
- Missing supervisor decisions, reasoning, searches

**Root Cause**: 
- Trace events collected during streaming but not persisted
- `update_state()` doesn't work during streaming
- Trace saved before all events collected

**Solution**: 
The `ensure_trace_completeness()` function in `agent/utils/helpers.py`:
```python
def ensure_trace_completeness(thread_id, expected_trace):
    # Checks if trace is complete, replaces if incomplete
    # Called after graph execution completes
```

**Prevention**: 
- Always collect trace events during entire stream
- Call `ensure_trace_completeness()` after graph execution
- Don't rely on `update_state()` during streaming

---

## Best Practices

### 1. Always Use DatabaseManager

**Do**:
```python
from db_utils import get_database_manager

db_manager = get_database_manager()
session = db_manager.get_session()
try:
    # Use session
finally:
    session.close()
```

**Don't**:
```python
# Don't create sessions manually
# Don't use raw SQL queries outside DatabaseManager
```

### 2. Initialize Schema on Startup

**Do**:
```python
@app.on_event("startup")
async def startup_event():
    db_manager = get_database_manager()
    db_manager.initialize_schema()
    setup_checkpointer(_checkpointer)
```

**Don't**:
```python
# Don't skip schema initialization
# Don't assume tables exist
```

### 3. Handle Checkpointer Setup Properly

**Do**:
```python
from db_utils.db_setup import setup_checkpointer
from agent import _checkpointer

setup_checkpointer(_checkpointer)  # Handles all setup logic
```

**Don't**:
```python
# Don't call checkpointer.setup() directly without verification
# Don't skip checkpoints table verification
```

### 4. Use Transactions Properly

**Do**:
```python
session = db_manager.get_session()
try:
    # Multiple operations
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```

**Don't**:
```python
# Don't forget to commit
# Don't forget to rollback on errors
# Don't forget to close sessions
```

### 5. Query Messages Efficiently

**Do**:
```python
# Use DatabaseManager methods
messages = db_manager.get_thread_messages_with_traces(thread_id)
```

**Don't**:
```python
# Don't query LangGraph state directly for UI
# Don't parse complex nested checkpoint structures
```

---

## Troubleshooting

### Check Database Connection

```python
from db_utils import get_database_manager

try:
    db_manager = get_database_manager()
    session = db_manager.get_session()
    session.execute(text("SELECT 1"))
    print("✓ Database connection successful")
except Exception as e:
    print(f"✗ Database connection failed: {e}")
```

### Verify Tables Exist

```sql
-- Check custom tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('threads', 'messages', 'execution_traces');

-- Check LangGraph tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'checkpoint%';
```

### Check Checkpointer Setup

```python
from agent import _checkpointer
from db_utils.db_setup import setup_checkpointer

if _checkpointer:
    print(f"Checkpointer type: {type(_checkpointer)}")
    print(f"Has setup method: {hasattr(_checkpointer, 'setup')}")
    setup_checkpointer(_checkpointer)
else:
    print("Checkpointer not available")
```

### Verify Checkpoints Table

```sql
-- Check if checkpoints table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'checkpoints'
);

-- Check table structure
\d checkpoints
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `relation "checkpoints" does not exist` | Missing checkpoints table | Run `setup_checkpointer(_checkpointer)` |
| `relation "threads" does not exist` | Schema not initialized | Run `db_manager.initialize_schema()` |
| `Failed to create PostgresSaver` | Connection string issue | Check `POSTGRES_CONNECTION_STRING` format |
| `Foreign key constraint violation` | Table creation order | Use `initialize_schema()` instead of manual creation |
| `Checkpointer not available` | Environment variable not set | Set `POSTGRES_CONNECTION_STRING` |

---

## File Structure

```
polyplexity/backend/
├── db_utils/
│   ├── __init__.py              # Exports DatabaseManager, checkpointer utils
│   ├── db_config.py             # Connection string and PostgresSaver creation
│   ├── db_schema.py             # SQLAlchemy ORM models (Thread, Message, ExecutionTrace)
│   ├── database_manager.py     # DatabaseManager class for CRUD operations
│   └── db_setup.py              # Checkpointer setup and verification
├── main.py                      # FastAPI app with startup event
└── docs/
    └── DATABASE.md              # This file
```

---

## Key Functions Reference

### DatabaseManager Methods

- `initialize_schema()`: Create all custom tables if they don't exist
- `reset_database()`: Drop all tables and recreate (⚠️ deletes all data)
- `save_thread_name(thread_id, name)`: Save or update thread name
- `save_message(thread_id, role, content)`: Save a message
- `save_execution_trace(message_id, event_type, event_data)`: Save trace event
- `get_thread_messages(thread_id)`: Get all messages for a thread
- `get_thread_messages_with_traces(thread_id)`: Get messages with execution traces
- `delete_thread(thread_id)`: Delete thread and all related data

### Setup Functions

- `setup_checkpointer(checkpointer)`: Setup LangGraph checkpointer tables
- `create_checkpointer()`: Create PostgresSaver instance from connection string
- `get_database_manager()`: Get global DatabaseManager instance

---

## Migration Notes

### From Legacy System

If migrating from the legacy database system:

1. **Backup existing data** (if any)
2. **Drop legacy tables** (if needed):
   ```sql
   DROP TABLE IF EXISTS old_table_name CASCADE;
   ```
3. **Run initialization**:
   ```python
   db_manager = get_database_manager()
   db_manager.initialize_schema()
   setup_checkpointer(_checkpointer)
   ```
4. **Migrate data** (if needed) using custom scripts

---

## Summary

- **Use hybrid persistence**: LangGraph checkpointer for agent state, custom tables for UI
- **Always initialize schema**: Call `initialize_schema()` and `setup_checkpointer()` on startup
- **Use DatabaseManager**: Don't create sessions or queries manually
- **Handle checkpoints table**: The setup script automatically creates it if missing
- **Follow best practices**: Use transactions, close sessions, handle errors properly

For questions or issues, refer to the troubleshooting section or check the code comments in `db_utils/` modules.

