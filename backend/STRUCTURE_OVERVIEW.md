# Backend Structure Overview

This document provides a comprehensive overview of the backend folder structure, explaining how `polyplexity_agent` works as an installable package and what each component does.

## High-Level Architecture

The backend follows a **two-tier architecture**:

1. **Application Layer** (`backend/` root) - FastAPI application that serves HTTP endpoints
2. **Package Layer** (`polyplexity_agent/`) - Installable Python package containing all agent logic

### Why `polyplexity_agent` is an Installable Package

The `polyplexity_agent` directory is structured as an installable Python package (via `pip install -e .`) for several key benefits:

- **Clean Imports**: Instead of relative imports like `from ..graphs import agent_graph`, you can use `from polyplexity_agent.graphs import agent_graph`
- **Reusability**: The package can be imported and used in other projects or scripts
- **Separation of Concerns**: Application logic (FastAPI routes) is separated from agent logic (LangGraph nodes)
- **Better IDE Support**: IDEs can properly resolve imports and provide autocomplete
- **Testability**: Tests can import the package cleanly without path manipulation

**Installation**: After running `cd polyplexity_agent && pip install -e .`, you can import from anywhere:
```python
from polyplexity_agent import main_graph, _checkpointer, run_research_agent
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.db_utils import get_database_manager
```

## Root Level (`backend/`)

The root level contains application-level files and directories:

### Core Application Files

- **`main.py`** - FastAPI application that wraps the LangGraph agent
  - Defines HTTP endpoints (`/chat`, `/threads`, `/health`)
  - Handles SSE streaming for real-time updates
  - Manages CORS and request/response handling
  - Imports from the installed `polyplexity_agent` package

- **`requirements.txt`** - Application-level Python dependencies
  - Includes FastAPI, uvicorn, and other runtime dependencies
  - Separate from `polyplexity_agent/requirements.txt` (package dependencies)

- **`.env.example`** - Template for environment variables
  - Documents required API keys (TAVILY_API_KEY, GROQ_API_KEY)
  - Database connection string template
  - Model configuration options

### Documentation and Rules

- **`PROJECT_STRUCTURE.md`** - Guidelines for project structure and naming conventions
- **`rules/`** - Documentation directory containing:
  - `BACKEND_RULES.md` - Backend-specific development rules
  - `CODING_STYLE.md` - Code style guidelines
  - `DATABASE.md` - Database usage and schema documentation
  - `MARKET_RESEARCH_PRODUCTION.md` - Market research feature documentation
  - `STREAM_RULES.md` - Streaming event format standards

### Test Suite

- **`tests/`** - Comprehensive test suite that mirrors the package structure
  - `conftest.py` - Shared pytest fixtures (mock LLM, database, etc.)
  - `fixtures/` - Test data, sample states, and mock responses
  - `graphs/` - Tests for graph nodes and state management
  - `integration/` - Integration tests for subgraphs and end-to-end flows
  - `scripts/` and `run_graphs/` - Utility scripts (excluded from pytest discovery)
  - See `tests/README.md` for detailed testing documentation

### Utilities

- **`utils/`** - Backend-level utility modules (currently minimal)

## Installable Package (`polyplexity_agent/`)

The `polyplexity_agent` directory is a complete Python package that contains all the agent logic, graph definitions, and supporting infrastructure.

### Package Structure

```
polyplexity_agent/
├── __init__.py              # Package exports (lazy imports)
├── entrypoint.py            # High-level API functions
├── models.py                # Pydantic models for structured outputs
├── orchestrator.py          # Deprecated (re-exports from state_manager)
├── pyproject.toml           # Package metadata and build configuration
├── requirements.txt         # Package dependencies
│
├── config/                  # Configuration management
│   ├── settings.py          # Application settings (models, paths, retries)
│   └── secrets.py          # Secrets management (database, API keys)
│
├── graphs/                  # LangGraph definitions
│   ├── agent_graph.py       # Main supervisor graph construction
│   ├── state.py             # TypedDict state definitions
│   ├── nodes/              # Node implementations
│   │   ├── supervisor/     # Main graph nodes
│   │   ├── researcher/     # Research subgraph nodes
│   │   └── market_research/ # Market research nodes
│   └── subgraphs/           # Subgraph definitions
│       ├── researcher.py    # Researcher subgraph
│       └── market_research.py # Market research subgraph
│
├── streaming/               # SSE and event handling
│   ├── sse.py              # SSE formatting and async generators
│   ├── event_processor.py  # Event normalization to envelope format
│   ├── event_serializers.py # Event serialization utilities
│   └── stream_writer.py    # Stream writer helpers for nodes
│
├── db_utils/                # Database utilities
│   ├── database_manager.py  # SQLAlchemy ORM and CRUD operations
│   ├── db_config.py         # Database configuration
│   ├── db_schema.py         # SQLAlchemy models (Thread, Message)
│   └── db_setup.py         # Checkpointer table setup
│
├── tools/                   # External tool integrations
│   └── polymarket.py        # Polymarket API client
│
├── prompts/                 # LLM prompts
│   ├── supervisor.py        # Supervisor decision prompts
│   ├── researcher.py        # Research query generation prompts
│   ├── market_prompts.py    # Market research prompts
│   ├── response_generator.py # Final report generation prompts
│   ├── system_prompts.py    # System-level prompts
│   └── thread_prompts.py    # Thread naming prompts
│
├── utils/                   # Utility functions
│   ├── helpers.py           # Common helpers (LLM creation, date formatting)
│   ├── state_logger.py      # State logging to files
│   └── state_manager.py     # Global state management (main_graph singleton)
│
├── logging/                 # Structured logging
│   └── logger.py           # structlog logger setup
│
├── testing/                # Testing utilities
│   └── draw_graph.py       # Graph visualization utilities
│
└── docs/                   # Documentation
    ├── ARCHITECTURE.md      # Architecture guide
    ├── DEVELOPMENT.md       # Development guidelines
    ├── TESTING.md          # Testing guide
    └── USAGE.md            # Usage documentation
```

### Core Entry Points

#### `__init__.py`
Package initialization with lazy imports for performance:
- Exports: `run_research_agent`, `main_graph`, `_checkpointer`
- Uses `__getattr__` for lazy loading to avoid importing heavy dependencies upfront

#### `entrypoint.py`
High-level API functions for external callers:
- **`run_research_agent(message, thread_id, graph)`** - Main function that executes the research agent workflow
  - Handles thread initialization and state management
  - Streams events from graph execution
  - Manages state logging and trace completeness
- **`create_default_graph()`** - Creates default agent graph with default settings

#### `pyproject.toml`
Package metadata and build configuration:
- Defines package name, version, dependencies
- Configures setuptools for package discovery
- Includes pytest configuration for test discovery

### Configuration (`config/`)

#### `settings.py`
Application settings using Pydantic BaseSettings:
- Model configuration (model_name, temperature)
- Thread naming model settings
- Retry configuration
- State logs directory
- Polymarket event filtering settings
- Supports environment variable overrides via `.env` file

#### `secrets.py`
Secrets management and database connection:
- `get_postgres_connection_string()` - Retrieves PostgreSQL connection string from environment
- `create_checkpointer()` - Creates LangGraph PostgresSaver checkpointer if database is configured
- `is_checkpointing_available()` - Checks if database is configured
- Handles connection string format conversion for LangGraph compatibility

### Graph System (`graphs/`)

The graph system implements a multi-agent architecture using LangGraph.

#### `agent_graph.py`
Main supervisor graph construction:
- **`create_agent_graph(settings, checkpointer)`** - Builds and compiles the main supervisor graph
  - Creates StateGraph with SupervisorState
  - Adds all supervisor nodes (supervisor, call_researcher, final_report, etc.)
  - Defines edges and conditional routing via `route_supervisor()`
  - Compiles graph with checkpointer for thread persistence
  - Generates graph visualization

**Graph Flow**:
```
START → supervisor → [conditional routing]
                      ├─→ call_researcher → supervisor (loop)
                      ├─→ call_market_research → rewrite_polymarket_response
                      ├─→ final_report → summarize_conversation → END
                      ├─→ direct_answer → summarize_conversation → END
                      └─→ clarification → END
```

#### `state.py`
TypedDict state definitions for type safety:
- **`SupervisorState`** - Main graph state (user_request, research_notes, final_report, etc.)
- **`ResearcherState`** - Research subgraph state (topic, queries, search_results, research_summary)
- **`MarketResearchState`** - Market research subgraph state (original_topic, market_queries, approved_markets, etc.)
- Uses `Annotated` reducers for state accumulation (e.g., `operator.add` for lists)

#### `nodes/` - Node Implementations

Nodes are organized by subgraph:

**`supervisor/`** - Main graph nodes:
- `supervisor.py` - Decision-making node (research/finish/clarify)
- `call_researcher.py` - Invokes researcher subgraph
- `call_market_research.py` - Invokes market research subgraph
- `direct_answer.py` - Generates direct answer without research
- `final_report.py` - Generates final report from research notes
- `rewrite_polymarket_response.py` - Creates Polymarket recommendations blurb
- `clarification.py` - Asks user for clarification
- `summarize_conversation.py` - Summarizes conversation history

**`researcher/`** - Research subgraph nodes:
- `generate_queries.py` - Generates search queries from topic
- `perform_search.py` - Executes Tavily web searches
- `synthesize_research.py` - Synthesizes search results into research summary

**`market_research/`** - Market research subgraph nodes:
- `generate_market_queries.py` - Generates Polymarket tag queries
- `fetch_markets.py` - Fetches markets from Polymarket API
- `process_and_rank_markets.py` - Processes and ranks markets by relevance
- `evaluate_markets.py` - Evaluates markets for approval

#### `subgraphs/`
Subgraph definitions that wrap node collections:
- `researcher.py` - Researcher subgraph (queries → search → synthesize)
- `market_research.py` - Market research subgraph (queries → fetch → rank → evaluate)

### Streaming (`streaming/`)

All streaming logic is centralized here to handle Server-Sent Events (SSE) for real-time updates.

#### `sse.py`
SSE formatting and async generators:
- `format_sse_event(event)` - Formats event envelope as SSE data line
- `create_sse_generator(stream)` - Creates async generator for SSE streaming
- `process_update_events()` - Converts state updates to envelope format
- Handles event normalization and envelope wrapping

#### `event_processor.py`
Event normalization and processing:
- `normalize_event(event)` - Normalizes events to standardized envelope format
- Handles backward compatibility with old event formats
- Ensures all events follow the envelope structure: `{type, event, payload, timestamp, node}`

#### `event_serializers.py`
Event serialization utilities:
- `serialize_event()` - Creates standardized event envelope
- `serialize_trace_event()` - Serializes trace events
- `serialize_custom_event()` - Serializes custom events
- `serialize_state_update()` - Serializes state update events

#### `stream_writer.py`
Stream writer helpers for nodes:
- Provides convenience functions for nodes to stream events
- `stream_event()` - Stream generic events
- `stream_trace_event()` - Stream trace events
- `stream_custom_event()` - Stream custom events
- `stream_state_update()` - Stream state updates

### Database (`db_utils/`)

Database utilities for thread persistence and message storage.

#### `database_manager.py`
SQLAlchemy ORM and CRUD operations:
- **`DatabaseManager`** class - Centralized database manager
  - Thread CRUD operations (create, get, list, delete)
  - Message CRUD operations (save, get by thread)
  - Schema initialization
  - Database reset functionality
- **`get_database_manager()`** - Singleton factory function
- Handles database errors gracefully (continues if database unavailable)

#### `db_schema.py`
SQLAlchemy models:
- **`Thread`** - Thread table model (thread_id, name, updated_at, message_count)
- **`Message`** - Message table model (message_id, thread_id, role, content, execution_trace, timestamp)

#### `db_config.py`
Database configuration:
- Database connection setup
- SQLAlchemy engine and session factory configuration

#### `db_setup.py`
Checkpointer table setup:
- `setup_checkpointer()` - Ensures LangGraph checkpoints table exists
- `checkpoints_table_exists()` - Checks if table exists
- Called during application startup

### Tools (`tools/`)

External service integrations.

#### `polymarket.py`
Polymarket API client:
- `search_markets(tags, max_results)` - Searches Polymarket for markets by tags
- `get_market_details(slug)` - Gets detailed market information
- Handles API requests and response parsing
- Extracts market data (clobTokenIds, outcomes, prices, etc.)

### Prompts (`prompts/`)

LLM prompt templates organized by functionality.

- **`supervisor.py`** - Supervisor decision-making prompts
- **`researcher.py`** - Research query generation prompts
- **`market_prompts.py`** - Market research prompts (tag selection, market ranking, evaluation)
- **`response_generator.py`** - Final report generation prompts (concise, report formats)
- **`system_prompts.py`** - System-level prompts
- **`thread_prompts.py`** - Thread name generation prompts

All prompts use format strings or templates for dynamic content injection.

### Utilities (`utils/`)

Common utility functions.

#### `helpers.py`
Common helper functions:
- `create_llm_model()` - Creates ChatGroq LLM model instance
- `format_date()` - Formats current date
- `save_messages_and_trace()` - Saves messages and execution trace to database
- `ensure_trace_completeness()` - Ensures execution trace is complete
- `log_node_state()` - Logs node state for debugging

#### `state_logger.py`
State logging to files:
- **`StateLogger`** class - Logs state transitions to files
- Used for debugging and development
- Writes state snapshots to configured directory

#### `state_manager.py`
Global state management:
- **`main_graph`** - Singleton main graph instance
- **`_checkpointer`** - Global checkpointer instance
- **`_state_logger`** - Global state logger instance
- Provides setter functions for dependency injection
- `ensure_checkpointer_setup()` - Ensures checkpointer tables are created

### Logging (`logging/`)

Structured logging setup.

#### `logger.py`
Structured logging using structlog:
- `get_logger(name)` - Gets logger instance for a module
- Configures structlog with JSON output
- Supports log levels via `LOG_LEVEL` environment variable
- Provides machine-friendly logs for production

### Testing (`testing/`)

Testing utilities.

#### `draw_graph.py`
Graph visualization utilities:
- Functions to visualize LangGraph structure
- Generates graph diagrams for documentation

### Documentation (`docs/`)

Comprehensive documentation:
- **`ARCHITECTURE.md`** - Architecture guide explaining components and data flow
- **`DEVELOPMENT.md`** - Development guidelines and best practices
- **`TESTING.md`** - Testing guide with examples
- **`USAGE.md`** - Usage documentation and API reference

### Models (`models.py`)

Pydantic models for structured LLM outputs:
- **`SearchQueries`** - Output model for search query generation
- **`SupervisorDecision`** - Output model for supervisor decisions
- **`MarketQueries`** - Output model for market query generation
- **`RankedMarkets`** - Output model for market ranking
- **`ApprovedMarkets`** - Output model for market evaluation

These models ensure type-safe structured outputs from LLM calls.

## Import Pattern Explanation

### How Installation Works

When you run `pip install -e .` from the `polyplexity_agent/` directory:

1. **Package Registration**: Python registers `polyplexity_agent` as an importable package
2. **Editable Mode**: The `-e` flag makes it editable, so changes to source files are immediately available
3. **Path Addition**: The package directory is added to Python's import path

### Import Examples

After installation, you can import from anywhere:

```python
# High-level API
from polyplexity_agent import run_research_agent, main_graph, _checkpointer

# Graph components
from polyplexity_agent.graphs.agent_graph import create_agent_graph
from polyplexity_agent.graphs.state import SupervisorState, ResearcherState

# Database utilities
from polyplexity_agent.db_utils import get_database_manager
from polyplexity_agent.db_utils.db_setup import setup_checkpointer

# Configuration
from polyplexity_agent.config import Settings
from polyplexity_agent.config.secrets import get_postgres_connection_string

# Streaming
from polyplexity_agent.streaming import create_sse_generator
from polyplexity_agent.streaming.event_serializers import serialize_event

# Tools
from polyplexity_agent.tools.polymarket import search_markets

# Utilities
from polyplexity_agent.utils.helpers import create_llm_model
```

### Benefits

- **No Relative Imports**: Clean absolute imports from package root
- **IDE Support**: IDEs can resolve imports and provide autocomplete
- **Reusability**: Package can be used in other projects
- **Testability**: Tests can import cleanly without path manipulation
- **Separation**: Application code (main.py) is separate from agent logic

## Data Flow

### Request Flow

1. **HTTP Request** → `main.py` receives POST request to `/chat`
2. **Package Import** → `main.py` imports `run_research_agent` from `polyplexity_agent`
3. **Entry Point** → `entrypoint.py` initializes state and graph
4. **Graph Execution** → `agent_graph.py` executes supervisor graph
5. **Node Processing** → Nodes process state and call subgraphs
6. **Subgraph Execution** → Researcher or market research subgraphs execute
7. **Event Streaming** → Events are streamed via SSE back to client
8. **State Updates** → State is updated and persisted (database/checkpointer)
9. **Response** → Final report is generated and streamed to client

### State Flow

State flows through TypedDict definitions:
- **SupervisorState** - Main graph state (user_request → research_notes → final_report)
- **ResearcherState** - Research subgraph state (topic → queries → search_results → research_summary)
- **MarketResearchState** - Market research state (original_topic → market_queries → approved_markets)

State is immutable - nodes return state updates that are merged into the current state.

### Event Streaming Flow

1. **Node Execution** → Node calls `stream_event()` or similar helper
2. **Event Serialization** → Event is serialized to envelope format
3. **SSE Formatting** → Event is formatted as SSE data line
4. **Streaming** → Event is yielded from async generator
5. **Client Delivery** → FastAPI streams event to client via SSE

## Key Design Principles

1. **Separation of Concerns**: Application layer (FastAPI) is separate from agent logic (LangGraph)
2. **Package Structure**: Agent logic is installable package for clean imports
3. **Type Safety**: TypedDict for state, Pydantic for structured outputs
4. **Event-Driven**: All updates flow through standardized event envelope format
5. **Modularity**: Nodes are independent, composable units
6. **Testability**: Clear separation allows easy mocking and testing
7. **Documentation**: Comprehensive docs in `docs/` directory

## Summary

The backend is structured as a **two-tier system**:

- **Application Layer** (`backend/`): FastAPI server that handles HTTP requests and SSE streaming
- **Package Layer** (`polyplexity_agent/`): Installable Python package containing all agent logic

The package is installed with `pip install -e .` which enables clean imports like `from polyplexity_agent import main_graph`. This architecture provides:

- Clean separation between HTTP handling and agent logic
- Reusable package that can be imported elsewhere
- Better IDE support and type checking
- Easier testing and development
- Clear organization of components by responsibility
