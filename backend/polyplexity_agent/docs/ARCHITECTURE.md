# Architecture Guide

This document explains the architecture of the `polyplexity_agent` library, including component structure, data flow, state management, event system, and checkpointing.

## Table of Contents

1. [Package Structure](#package-structure)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [State Management](#state-management)
5. [Event System](#event-system)
6. [Checkpointing](#checkpointing)
7. [Graph Structure](#graph-structure)

## Package Structure

```
polyplexity_agent/
├── __init__.py              # Package exports (lazy imports)
├── entrypoint.py            # High-level API (run_research_agent, create_default_graph)
├── config/                  # Configuration management
│   ├── settings.py          # Application settings (model config, paths)
│   └── secrets.py           # Secrets management (database, API keys)
├── graphs/                  # LangGraph definitions
│   ├── agent_graph.py       # Main supervisor graph construction
│   ├── state.py             # State TypedDict definitions
│   ├── nodes/               # Node implementations
│   │   ├── supervisor/      # Main graph nodes
│   │   ├── researcher/      # Researcher subgraph nodes
│   │   └── market_research/ # Market research subgraph nodes
│   └── subgraphs/           # Subgraph definitions
│       ├── researcher.py    # Researcher subgraph
│       └── market_research.py # Market research subgraph
├── streaming/               # SSE and event handling
│   ├── sse.py               # SSE formatting and generator
│   ├── event_processor.py   # Event normalization and processing
│   ├── event_serializers.py # Event serialization utilities
│   └── stream_writer.py     # Stream writer helpers for nodes
├── logging/                 # Structured logging
│   └── logger.py            # structlog logger setup
├── utils/                   # Utility functions
│   ├── helpers.py           # Common helper functions
│   ├── state_logger.py      # State logging to files
│   └── state_manager.py     # Global state management (main_graph, _checkpointer)
├── tools/                   # External tool integrations
│   └── polymarket.py        # Polymarket API client
├── prompts/                 # LLM prompts
│   ├── supervisor.py        # Supervisor node prompts
│   ├── researcher.py        # Researcher prompts
│   └── ...
└── db_utils/                # Database utilities
    ├── database_manager.py  # Database CRUD operations
    ├── db_config.py         # Database configuration
    └── db_schema.py         # SQLAlchemy models
```

## Core Components

### entrypoint.py - High-Level API

**Purpose**: Provides the main entry point for external callers (e.g., `main.py`).

**Key Functions**:

- **`run_research_agent(message, thread_id, graph)`**:
  - Main function that executes the research agent workflow
  - Handles thread initialization and state management
  - Streams events from graph execution
  - Manages state logging and trace completeness

- **`create_default_graph()`**:
  - Creates a default agent graph with default settings
  - Convenience function for simple use cases

**Responsibilities**:
- Thread ID generation (if not provided)
- Initial state construction (fresh vs follow-up)
- Graph execution orchestration
- Event streaming coordination
- State logger lifecycle management

### graphs/agent_graph.py - Main Graph Construction

**Purpose**: Builds and compiles the main supervisor agent graph.

**Key Function**:

- **`create_agent_graph(settings, checkpointer)`**:
  - Creates StateGraph with SupervisorState
  - Adds all supervisor nodes
  - Defines edges and conditional routing
  - Compiles graph with checkpointer
  - Generates graph visualization

**Graph Structure**:
```
START → supervisor → [conditional routing]
                      ├─→ call_researcher → supervisor (loop)
                      ├─→ final_report → summarize_conversation → END
                      ├─→ direct_answer → summarize_conversation → END
                      └─→ clarification → summarize_conversation → END
```

**Routing Logic** (`route_supervisor`):
- `CLARIFY:*` → clarification node
- `FINISH` → final_report (if research_notes exist) or direct_answer
- Based on `answer_format` and `iterations` count → final_report or call_researcher

### graphs/state.py - State Definitions

**Purpose**: Defines TypedDict schemas for all graph states.

**State Types**:

1. **SupervisorState**: Main graph state
   - Accumulates: `research_notes`, `conversation_history`, `execution_trace`
   - Fields: `user_request`, `next_topic`, `final_report`, `iterations`, etc.

2. **ResearcherState**: Researcher subgraph state
   - Accumulates: `search_results` (via `operator.add`)
   - Fields: `topic`, `queries`, `research_summary`, `query_breadth`

3. **MarketResearchState**: Market research subgraph state
   - Accumulates: `reasoning_trace` (via `operator.add`)
   - Fields: `original_topic`, `market_queries`, `candidate_markets`, etc.

**State Accumulation**:
- Uses `Annotated[Type, reducer]` for fields that accumulate across nodes
- `operator.add` for lists (concatenates)
- `manage_chat_history` for conversation_history (structured messages)

### graphs/nodes/ - Node Implementations

**Organization**: Nodes are organized by subgraph:
- `supervisor/`: Main graph nodes (supervisor, call_researcher, final_report, etc.)
- `researcher/`: Researcher subgraph nodes (generate_queries, perform_search, synthesize_research)
- `market_research/`: Market research nodes (generate_market_queries, fetch_markets, etc.)

**Node Pattern**:
```python
def node_name(state: StateType):
    """Node function that processes state and returns updates."""
    # 1. Log state (before)
    # 2. Emit trace events
    # 3. Perform work (LLM calls, tool invocations)
    # 4. Emit custom events
    # 5. Return state updates
    return {"field": "value", "execution_trace": [...]}
```

**Key Responsibilities**:
- State transformation
- Event emission (via `stream_custom_event`, `stream_trace_event`)
- Error handling (emit error events, log, re-raise)
- State logging (via `log_node_state`)

### graphs/subgraphs/ - Subgraph Definitions

**Purpose**: Define reusable subgraphs that can be invoked from main graph nodes.

**Researcher Subgraph** (`researcher.py`):
- **Flow**: `generate_queries` → `map_queries` (parallel) → `perform_search` → `synthesize_research`
- **Parallel Execution**: Uses `Send` to invoke `perform_search` for each query in parallel
- **State**: ResearcherState (topic → research_summary)

**Market Research Subgraph** (`market_research.py`):
- **Flow**: `generate_market_queries` → `fetch_markets` → `process_and_rank_markets` → `evaluate_markets`
- **State**: MarketResearchState (original_topic → approved_markets)

**Integration**: Subgraphs are invoked from main graph nodes:
- `call_researcher_node` invokes `researcher_graph.stream()`
- Events from subgraphs are forwarded to main graph stream via `get_stream_writer()`

### streaming/ - Event Processing

**Purpose**: Handles SSE formatting and event normalization.

**Key Modules**:

1. **`sse.py`**: SSE formatting
   - `create_sse_generator()`: Converts LangGraph iterator to async SSE generator
   - `format_sse_event()`: Formats event envelope as SSE data line
   - Handles custom events and state updates
   - Emits completion and error events

2. **`event_processor.py`**: Event normalization
   - `process_custom_events()`: Processes custom events from stream
   - `process_update_events()`: Converts state updates to envelope format
   - `normalize_event()`: Normalizes events to standard envelope format

3. **`event_serializers.py`**: Event creation utilities
   - `create_trace_event()`: Creates trace event envelopes
   - Serialization helpers for different event types

4. **`stream_writer.py`**: Stream writer helpers
   - `stream_custom_event()`: Emit custom events from nodes
   - `stream_trace_event()`: Emit trace events from nodes
   - Uses LangGraph's `get_stream_writer()` to forward events

### config/ - Configuration Management

**`settings.py`**: Application settings
- Model configuration (model_name, temperature, retries)
- State logs directory
- Uses Pydantic BaseSettings for environment variable support

**`secrets.py`**: Secrets management
- Database connection string
- API keys (Tavily, etc.)
- Checkpointer creation
- Environment variable loading

### utils/state_manager.py - Global State Management

**Purpose**: Manages global application state (main_graph, _checkpointer).

**Key Components**:

- **`main_graph`**: Compiled LangGraph instance (lazy-loaded)
- **`_checkpointer`**: LangGraph checkpointer instance (created at import time)
- **`_state_logger`**: Global state logger instance (set per request)

**Lazy Loading**: `main_graph` is lazy-loaded via `__getattr__` to avoid circular imports.

## Data Flow

### Request Flow

```
HTTP POST /chat (main.py)
    ↓
run_research_agent(query, thread_id)
    ↓
Create/retrieve graph instance
    ↓
Initialize state (fresh or follow-up)
    ↓
graph.stream(initial_state, config, stream_mode)
    ↓
[Graph execution - see State Flow]
    ↓
Yield (mode, data) tuples
    ↓
create_sse_generator(event_iterator)
    ↓
Process events → SSE format
    ↓
FastAPI StreamingResponse → Client
```

### State Flow

```
Initial State (SupervisorState)
    ↓
supervisor_node
    ├─→ Assess request
    ├─→ Decide next action
    └─→ Update: next_topic, iterations
    ↓
[Conditional Routing]
    ├─→ call_researcher_node
    │   ├─→ Invoke researcher_graph.stream()
    │   │   ├─→ generate_queries_node (ResearcherState)
    │   │   ├─→ perform_search_node (parallel)
    │   │   └─→ synthesize_research_node
    │   └─→ Update: research_notes
    │
    ├─→ final_report_node
    │   ├─→ Generate final report
    │   └─→ Update: final_report, execution_trace
    │
    ├─→ direct_answer_node
    │   └─→ Update: final_report
    │
    └─→ clarification_node
        └─→ Update: final_report
    ↓
summarize_conversation_node
    ├─→ Summarize conversation
    └─→ Update: conversation_summary, conversation_history
    ↓
END
```

### Event Flow

```
Node Execution
    ↓
stream_custom_event() / stream_trace_event()
    ↓
LangGraph stream_writer (get_stream_writer())
    ↓
(mode="custom", data=event_envelope)
    ↓
entrypoint.py: process_custom_events()
    ↓
normalize_event() → envelope format
    ↓
Yield to caller
    ↓
create_sse_generator()
    ↓
format_sse_event() → "data: {json}\n\n"
    ↓
FastAPI StreamingResponse
    ↓
Client receives SSE event
```

**Event Envelope Format**:
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

### Thread Flow

```
Request with thread_id
    ↓
run_research_agent(query, thread_id)
    ↓
Check existing state: graph.get_state(config)
    ├─→ If exists: Load conversation_summary, conversation_history
    └─→ If not: Start fresh
    ↓
Graph execution (updates state)
    ↓
State persisted via checkpointer (if available)
    ↓
Messages saved to database (via nodes)
    ↓
Next request with same thread_id → Loads previous state
```

## State Management

### State Accumulation

State fields that accumulate across nodes use `Annotated[Type, reducer]`:

```python
research_notes: Annotated[List[str], operator.add]  # Concatenates lists
conversation_history: Annotated[List[dict], manage_chat_history]  # Custom reducer
execution_trace: Annotated[List[dict], operator.add]  # Concatenates lists
```

**How it works**:
- LangGraph applies the reducer function when multiple nodes update the same field
- `operator.add` concatenates lists: `[1, 2] + [3, 4] = [1, 2, 3, 4]`
- `manage_chat_history` handles structured message format and deduplication

### State Updates

Nodes return dictionaries with state updates:

```python
def node_name(state: SupervisorState):
    return {
        "field": "new_value",  # Updates field
        "list_field": ["new_item"],  # Accumulates if Annotated with reducer
        "execution_trace": [event]  # Accumulates trace events
    }
```

**Important**: Nodes should only return fields they intend to update. Other fields are preserved automatically.

### State Persistence

State is persisted in two ways:

1. **LangGraph Checkpointer**: Stores complete graph state
   - Accessed via `graph.get_state(config)` and `graph.update_state()`
   - Used for conversation continuity

2. **Database Tables**: Stores structured data
   - `Thread`: Thread metadata
   - `Message`: Individual messages with execution traces
   - Accessed via `get_database_manager()`

## Event System

### Event Types

1. **Custom Events**: Application-specific events
   - Examples: `supervisor_decision`, `generated_queries`, `web_search_url`
   - Emitted via `stream_custom_event()`

2. **Trace Events**: Execution trace events
   - Examples: `node_call`, `reasoning`, `custom`
   - Emitted via `stream_trace_event()`
   - Collected in `execution_trace` field

3. **State Updates**: State change notifications
   - Emitted automatically by LangGraph when state updates
   - Processed via `process_update_events()`

4. **System Events**: System-level events
   - Examples: `thread_id`, `thread_name`, `complete`, `error`
   - Emitted by entrypoint or SSE generator

### Event Emission

**From Nodes**:
```python
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event

# Emit custom event
stream_custom_event("event_name", "node_name", {"data": "value"})

# Emit trace event
stream_trace_event("trace_type", "node_name", {"data": "value"})
```

**Event Forwarding** (from subgraphs):
```python
from langgraph.config import get_stream_writer

writer = get_stream_writer()
if writer:
    writer(event_dict)  # Forwards event to main graph stream
```

### Event Processing

Events flow through multiple processing stages:

1. **Node Emission**: Node calls `stream_custom_event()` or `stream_trace_event()`
2. **LangGraph Stream**: Event appears in `(mode="custom", data=event)` tuple
3. **Event Processing**: `process_custom_events()` normalizes events
4. **SSE Formatting**: `create_sse_generator()` formats as SSE
5. **Client Delivery**: FastAPI streams to client

## Checkpointing

### Checkpointer Creation

Checkpointer is created in `config/secrets.py`:

```python
def create_checkpointer():
    """Create LangGraph checkpointer if database is configured."""
    # Checks for database connection string
    # Creates PostgresCheckpointer if available
    # Returns None if database not configured
```

### Checkpointer Setup

Checkpointer setup happens in two places:

1. **Graph Compilation** (`agent_graph.py`):
   ```python
   checkpointer = ensure_checkpointer_setup(checkpointer)
   compiled_graph = builder.compile(checkpointer=checkpointer)
   ```

2. **FastAPI Startup** (`main.py`):
   ```python
   setup_checkpointer(_checkpointer)  # Ensures tables exist
   ```

### Thread Persistence

When a `thread_id` is provided:

1. **State Retrieval**: `graph.get_state({"configurable": {"thread_id": thread_id}})`
2. **State Updates**: LangGraph automatically persists state after each node execution
3. **State Loading**: Next request with same `thread_id` loads previous state

### Checkpointer Tables

LangGraph creates checkpoint tables:
- `checkpoints`: Graph state snapshots
- `checkpoint_blobs`: Large state blobs

Tables are created automatically on first use or via `setup_checkpointer()`.

## Graph Structure

### Main Graph (Supervisor)

```
START
  ↓
supervisor (decision node)
  ↓
[Conditional Routing]
  ├─→ call_researcher → supervisor (loop)
  ├─→ final_report → summarize_conversation → END
  ├─→ direct_answer → summarize_conversation → END
  └─→ clarification → summarize_conversation → END
```

**Nodes**:
- `supervisor`: Decides next action (research, finish, clarify)
- `call_researcher`: Invokes researcher subgraph
- `final_report`: Generates final report from research notes
- `direct_answer`: Provides direct answer (no research needed)
- `clarification`: Asks user for clarification
- `summarize_conversation`: Summarizes conversation and updates history

### Researcher Subgraph

```
START
  ↓
generate_queries
  ↓
[Parallel Execution via Send]
  ├─→ perform_search
  ├─→ perform_search
  └─→ perform_search
  ↓
synthesize_research
  ↓
END
```

**Nodes**:
- `generate_queries`: Breaks topic into search queries
- `perform_search`: Executes Tavily search (parallel)
- `synthesize_research`: Synthesizes all search results

### Market Research Subgraph

```
START
  ↓
generate_market_queries
  ↓
fetch_markets
  ↓
process_and_rank_markets
  ↓
evaluate_markets
  ↓
END
```

**Nodes**:
- `generate_market_queries`: Generates Polymarket search keywords
- `fetch_markets`: Fetches markets from Polymarket API
- `process_and_rank_markets`: Processes and ranks markets
- `evaluate_markets`: Evaluates markets for relevance

## Key Design Patterns

1. **Lazy Loading**: `main_graph` and imports are lazy-loaded to avoid circular dependencies
2. **State Accumulation**: Uses `Annotated` with reducers for accumulating fields
3. **Event Forwarding**: Subgraph events are forwarded to main graph stream
4. **Graceful Degradation**: Checkpointing is optional (continues without it)
5. **Structured Logging**: Uses structlog for machine-friendly logs
6. **Error Handling**: Errors are emitted as events before raising exceptions

## Integration Points

### External Callers (main.py)

- **Entry Point**: `run_research_agent(query, thread_id)`
- **Graph Access**: `main_graph` (for state retrieval)
- **Checkpointer**: `_checkpointer` (for thread deletion)
- **Streaming**: `create_sse_generator(event_iterator)`

### Node Development

- **State Access**: Receive state as function parameter
- **State Updates**: Return dict with updates
- **Event Emission**: Use `stream_custom_event()` or `stream_trace_event()`
- **Logging**: Use `get_logger(__name__)` for structured logging

### Subgraph Development

- **Graph Construction**: Use `StateGraph(StateType)` and `builder.compile()`
- **Event Forwarding**: Use `get_stream_writer()` to forward events
- **State Mapping**: Map main graph state to subgraph state
