# Usage Guide: Integrating polyplexity_agent with FastAPI

This guide explains how `main.py` integrates with the `polyplexity_agent` library to provide a FastAPI-based research agent service with Server-Sent Events (SSE) streaming.

## Table of Contents

1. [Package Installation](#package-installation)
2. [Key Imports](#key-imports)
3. [FastAPI Endpoint Integration](#fastapi-endpoint-integration)
4. [SSE Streaming Flow](#sse-streaming-flow)
5. [Thread Management](#thread-management)
6. [Database Integration](#database-integration)
7. [Error Handling](#error-handling)
8. [Startup Initialization](#startup-initialization)

## Package Installation

The `polyplexity_agent` package must be installed in editable mode before running `main.py`:

```bash
cd polyplexity/backend/polyplexity_agent
pip install -e .
```

This allows `main.py` to import from the installed package using standard Python import syntax:

```python
from polyplexity_agent import run_research_agent, main_graph, _checkpointer
```

**Why editable mode?** Editable installation (`-e`) allows code changes to be immediately available without reinstalling the package, which is essential during development.

## Key Imports

`main.py` imports the following components from `polyplexity_agent`:

### Core Entry Point

```python
from polyplexity_agent import run_research_agent, main_graph, _checkpointer
```

- **`run_research_agent`**: Main entry point function that executes the research agent workflow. Returns an iterator yielding `(mode, data)` tuples from LangGraph stream.
- **`main_graph`**: The compiled LangGraph instance (lazy-loaded via `utils.state_manager`).
- **`_checkpointer`**: LangGraph checkpointer instance for thread persistence (may be `None` if database not configured).

### Streaming Module

```python
from polyplexity_agent.streaming import create_sse_generator
```

- **`create_sse_generator`**: Converts LangGraph event iterator into async SSE generator for FastAPI StreamingResponse.

### Database Utilities

```python
from polyplexity_agent.db_utils import get_database_manager
from polyplexity_agent.db_utils.db_setup import setup_checkpointer
```

- **`get_database_manager`**: Returns singleton DatabaseManager instance for thread/message persistence.
- **`setup_checkpointer`**: Ensures LangGraph checkpointer tables are created in the database.

## FastAPI Endpoint Integration

### `/chat` Endpoint

The main chat endpoint integrates the library as follows:

```python
@app.post("/chat")
async def chat_agent(
    request: QueryRequest,
    thread_id: Optional[str] = Query(None)
):
    async def sse_generator():
        async for sse_line in create_sse_generator(
            run_research_agent(request.query, thread_id=thread_id)
        ):
            yield sse_line
    
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream"
    )
```

**Flow:**
1. Receives HTTP POST request with user query and optional `thread_id`
2. Calls `run_research_agent()` with query and thread_id
3. Wraps the iterator in `create_sse_generator()` to format events as SSE
4. Returns FastAPI `StreamingResponse` with `text/event-stream` media type

### Thread Management Endpoints

**`GET /threads`**: Lists all conversation threads
- Uses `get_database_manager()` to query Thread and Message tables
- Formats thread information including last message and message count

**`DELETE /threads/{thread_id}`**: Deletes a thread
- Uses `get_database_manager()` to delete thread (cascades to messages)
- Also deletes from LangGraph checkpointer if available: `_checkpointer.delete_thread(thread_id)`

**`GET /threads/{thread_id}/history`**: Retrieves conversation history
- First attempts to get messages from database table via `get_thread_messages_with_traces()`
- Falls back to LangGraph state via `main_graph.get_state(config)` if table is empty
- Handles both structured message format and legacy string format

## SSE Streaming Flow

The complete streaming flow from user request to client:

```
HTTP POST /chat
    ↓
run_research_agent(query, thread_id)
    ↓
LangGraph stream execution
    ↓ (yields events)
(mode, data) tuples
    ↓
create_sse_generator(event_iterator)
    ↓ (processes events)
SSE-formatted strings
    ↓
FastAPI StreamingResponse
    ↓
Client receives SSE events
```

### Event Processing

`create_sse_generator()` processes two types of events:

1. **Custom Events** (`mode == "custom"`):
   - Already in envelope format from nodes
   - Examples: `supervisor_decision`, `web_search_url`, `final_report_complete`
   - Processed via `process_custom_events()`

2. **State Updates** (`mode == "updates"`):
   - Dict mapping node names to state updates
   - Examples: `{"final_report": {"final_report": "..."}}`
   - Converted to envelope format and emitted as SSE

### Event Envelope Format

All events are normalized to a standard envelope format:

```json
{
  "type": "custom|trace|state_update|system|error|complete",
  "timestamp": 1234567890,
  "node": "supervisor|researcher|...",
  "event": "event_name",
  "payload": {
    // Event-specific data
  }
}
```

### Completion and Error Events

- **Completion**: Emitted when graph execution completes successfully
  ```json
  {
    "type": "complete",
    "event": "complete",
    "payload": {"response": "Final report content"}
  }
  ```

- **Error**: Emitted when an exception occurs during streaming
  ```json
  {
    "type": "error",
    "event": "error",
    "payload": {"error": "Error message"}
  }
  ```

## Thread Management

### Thread ID Generation

- If `thread_id` is not provided, `run_research_agent()` generates one: `thread_{uuid}`
- Thread ID is used for:
  - LangGraph checkpointing (state persistence)
  - Database thread/message storage
  - Conversation continuity across requests

### Thread Persistence

Thread state is persisted in two places:

1. **LangGraph Checkpointer**: Stores graph execution state
   - Accessed via `_checkpointer` (may be `None` if database not configured)
   - Used by `main_graph.get_state(config)` to retrieve conversation state

2. **Database Tables**: Stores structured thread and message data
   - `Thread` table: Thread metadata (thread_id, name, timestamps)
   - `Message` table: Individual messages with execution traces
   - Accessed via `get_database_manager()`

### Follow-up Conversations

When a `thread_id` is provided:

1. `run_research_agent()` checks for existing state via `graph.get_state(config)`
2. If state exists, initializes with:
   - Existing `conversation_summary`
   - Existing `conversation_history`
   - Existing `current_report_version`
   - New `user_request` (the follow-up question)
3. Graph execution continues with conversation context

## Database Integration

### Database Manager

`get_database_manager()` returns a singleton `DatabaseManager` instance that handles:

- Thread CRUD operations
- Message storage and retrieval
- Execution trace storage
- Thread name generation

### Checkpointer Setup

`setup_checkpointer()` ensures LangGraph checkpointer tables exist:

- Called during FastAPI startup event
- Creates checkpoint tables if they don't exist
- Handles errors gracefully (doesn't fail startup if database unavailable)

### Database Schema Initialization

On FastAPI startup:

```python
@app.on_event("startup")
async def startup_event():
    db_manager = get_database_manager()
    db_manager.initialize_schema()  # Creates tables if needed
    setup_checkpointer(_checkpointer)  # Creates checkpointer tables
```

## Error Handling

### Streaming Errors

Errors during graph execution are caught by `create_sse_generator()`:

```python
try:
    # Process events...
except Exception as e:
    error_event = format_error_event(str(e))
    yield format_sse_event(error_event)
    raise  # Re-raise to FastAPI error handler
```

The error event is streamed to the client before the exception is raised.

### Database Errors

Database operations in endpoints use try/except blocks:

- Errors are logged but don't crash the server
- Endpoints return appropriate HTTP status codes (404, 500)
- Fallback mechanisms (e.g., LangGraph state fallback for thread history)

### Checkpointer Errors

If checkpointer operations fail:

- Operations continue without checkpointing (graceful degradation)
- Warnings are logged but don't prevent graph execution
- Thread ID is still generated for database storage

## Startup Initialization

The FastAPI startup sequence:

1. **Database Schema Initialization**:
   ```python
   db_manager = get_database_manager()
   db_manager.initialize_schema()
   ```
   - Creates Thread, Message, ExecutionTrace tables if they don't exist
   - Does not drop existing data

2. **Checkpointer Setup**:
   ```python
   setup_checkpointer(_checkpointer)
   ```
   - Creates LangGraph checkpointer tables
   - Handles errors gracefully (continues if database unavailable)

3. **Package Imports**:
   - `main_graph` is lazy-loaded on first access (via `utils.state_manager.__getattr__`)
   - `_checkpointer` is created at module import time (may be `None`)

### Initialization Order

1. Package imports (`from polyplexity_agent import ...`)
2. FastAPI app creation (`app = FastAPI()`)
3. Startup event fires (`@app.on_event("startup")`)
4. Database and checkpointer setup
5. App ready to serve requests

## Example: Complete Request Flow

```python
# 1. Client sends POST /chat
POST /chat
Body: {"query": "What is the weather today?"}
Query: ?thread_id=thread_abc123

# 2. FastAPI endpoint receives request
@app.post("/chat")
async def chat_agent(request, thread_id):
    # 3. Call library entry point
    event_iterator = run_research_agent(request.query, thread_id=thread_id)
    
    # 4. Wrap in SSE generator
    async def sse_generator():
        async for sse_line in create_sse_generator(event_iterator):
            yield sse_line
    
    # 5. Return streaming response
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

# 6. Library executes graph
run_research_agent() → creates graph → streams events

# 7. Events flow through SSE generator
(mode, data) → envelope format → SSE format → client

# 8. Client receives events
data: {"type": "custom", "event": "supervisor_decision", ...}
data: {"type": "state_update", "event": "research_notes_added", ...}
data: {"type": "complete", "event": "complete", ...}
```

## Best Practices

1. **Always install package in editable mode** during development
2. **Handle None checkpointer** - Checkpointing is optional if database unavailable
3. **Use thread_id for conversation continuity** - Pass it in query params
4. **Handle streaming errors gracefully** - Errors are streamed to client before raising
5. **Use database fallbacks** - Check database first, fall back to LangGraph state if needed
6. **Initialize schema on startup** - Ensures tables exist before serving requests

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'polyplexity_agent'`

**Solution**: Install package in editable mode:
```bash
cd polyplexity/backend/polyplexity_agent
pip install -e .
```

### Checkpointer Not Working

**Problem**: Thread state not persisting

**Solution**: 
- Check database connection string in environment variables
- Verify `_checkpointer` is not `None`
- Check startup logs for checkpointer setup errors

### SSE Events Not Streaming

**Problem**: Client not receiving events

**Solution**:
- Verify `create_sse_generator()` is wrapping `run_research_agent()` iterator
- Check that `StreamingResponse` has correct `media_type="text/event-stream"`
- Ensure events are being yielded from graph nodes (check node implementations)
