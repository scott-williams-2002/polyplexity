# Development Guide: Adding New Features

This guide provides templates, patterns, and examples for adding new features to the `polyplexity_agent` library, including nodes, subgraphs, tools, streaming events, state modifications, and configuration.

## Table of Contents

1. [Adding a New Node](#adding-a-new-node)
2. [Adding a New Subgraph](#adding-a-new-subgraph)
3. [Adding a New Tool](#adding-a-new-tool)
4. [Adding Streaming Events](#adding-streaming-events)
5. [Modifying State](#modifying-state)
6. [Adding Configuration](#adding-configuration)
7. [Import Patterns](#import-patterns)
8. [Module Organization](#module-organization)

## Adding a New Node

### Template: Basic Node

```python
"""
[Node name] node for the [graph/subgraph] graph.

[Brief description of what the node does]
"""
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage

from polyplexity_agent.config import Settings
from polyplexity_agent.streaming.event_serializers import create_trace_event
from polyplexity_agent.graphs.state import [StateType]  # SupervisorState, ResearcherState, etc.
from polyplexity_agent.logging import get_logger
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.prompts.[module] import [PROMPT_CONSTANTS]
from polyplexity_agent.utils.helpers import (
    create_llm_model,
    format_date,
    log_node_state,
)

settings = Settings()
logger = get_logger(__name__)


def _helper_function(state: [StateType]) -> str:
    """
    Helper function for node logic.
    
    Args:
        state: Current graph state
        
    Returns:
        Result string
    """
    # Implementation here
    pass


def [node_name]_node(state: [StateType]):
    """
    [Node description].
    
    Args:
        state: Current graph state
        
    Returns:
        Dict with state updates
    """
    try:
        # Access state logger (adjust import based on graph type)
        from polyplexity_agent.utils.state_manager import _state_logger
        # OR for subgraph nodes:
        # from polyplexity_agent.graphs.subgraphs.[subgraph] import _state_logger
        
        # Log state before execution
        log_node_state(
            _state_logger,
            "[node_name]",
            "[GRAPH_TYPE]",  # "MAIN_GRAPH" or "SUBGRAPH"
            dict(state),
            "BEFORE",
            state.get("iterations", 0),  # Optional: iteration count
            "Additional info"  # Optional: additional context
        )
        
        # Emit trace event for node call
        node_call_event = create_trace_event("node_call", "[node_name]", {})
        stream_trace_event("node_call", "[node_name]", {})
        
        # Emit custom event (if needed)
        stream_custom_event("[event_name]", "[node_name]", {"data": "value"})
        
        # Perform work (LLM calls, tool invocations, etc.)
        result_value = _helper_function(state)
        
        # Create trace events for execution
        execution_event = create_trace_event("custom", "[node_name]", {
            "event": "[event_name]",
            "result": result_value
        })
        stream_trace_event("custom", "[node_name]", {
            "event": "[event_name]",
            "result": result_value
        })
        
        # Prepare state updates
        result = {
            "[field_name]": result_value,
            "execution_trace": [node_call_event, execution_event]
        }
        
        # Log state after execution
        log_node_state(
            _state_logger,
            "[node_name]",
            "[GRAPH_TYPE]",
            {**state, **result},
            "AFTER",
            state.get("iterations", 0),
            "Result summary"
        )
        
        return result
        
    except Exception as e:
        # Emit error event
        stream_custom_event("error", "[node_name]", {"error": str(e)})
        logger.error("[node_name]_error", error=str(e), exc_info=True)
        raise
```

### Node Location

Place nodes in the appropriate directory:

- **Main graph nodes**: `graphs/nodes/supervisor/[node_name].py`
- **Researcher subgraph nodes**: `graphs/nodes/researcher/[node_name].py`
- **Market research nodes**: `graphs/nodes/market_research/[node_name].py`

### Node Registration

**For main graph** (`graphs/agent_graph.py`):

```python
from polyplexity_agent.graphs.nodes.supervisor.[node_name] import [node_name]_node

# In create_agent_graph():
builder.add_node("[node_name]", [node_name]_node)
```

**For subgraph** (`graphs/subgraphs/[subgraph].py`):

```python
from polyplexity_agent.graphs.nodes.[subgraph].[node_name] import [node_name]_node

# In build_[subgraph]_subgraph():
builder.add_node("[node_name]", [node_name]_node)
```

### Node Export

Add to `graphs/nodes/[subgraph]/__init__.py`:

```python
from .[node_name] import [node_name]_node

__all__ = [
    # ... existing exports
    "[node_name]_node",
]
```

## Adding a New Subgraph

### Template: Subgraph Definition

```python
"""
[Subgraph name] subgraph implementation.

Handles [workflow description]: [Step 1] -> [Step 2] -> [Step 3]
"""
from typing import Optional

from langgraph.graph import END, START, StateGraph

from polyplexity_agent.graphs.nodes.[subgraph] import (
    [node1]_node,
    [node2]_node,
    [node3]_node,
)
from polyplexity_agent.graphs.state import [SubgraphState]  # ResearcherState, MarketResearchState, etc.

# Global state logger instance (for subgraph nodes)
_state_logger: Optional[object] = None


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


def build_[subgraph]_subgraph():
    """Build and compile the [subgraph name] subgraph."""
    builder = StateGraph([SubgraphState])
    
    # Add nodes
    builder.add_node("[node1]", [node1]_node)
    builder.add_node("[node2]", [node2]_node)
    builder.add_node("[node3]", [node3]_node)
    
    # Define edges
    builder.add_edge(START, "[node1]")
    builder.add_edge("[node1]", "[node2]")
    builder.add_edge("[node2]", "[node3]")
    builder.add_edge("[node3]", END)
    
    # Optional: Conditional edges
    # builder.add_conditional_edges(
    #     "[node1]",
    #     routing_function,
    #     {
    #         "path_a": "[node2]",
    #         "path_b": "[node3]",
    #     }
    # )
    
    return builder.compile()


def create_[subgraph]_graph():
    """Create the [subgraph name] subgraph."""
    return build_[subgraph]_subgraph()


# Compile the subgraph at module level
[subgraph]_graph = build_[subgraph]_subgraph()
```

### Subgraph State Definition

Add to `graphs/state.py`:

```python
class [SubgraphName]State(TypedDict, total=False):
    """
    State schema for the [subgraph name] subgraph.
    
    Fields:
        [field1]: [Description]
        [field2]: [Description]
    """
    [field1]: str
    [field2]: Annotated[List[str], operator.add]  # If accumulating
    [field3]: int
```

### Subgraph Integration

**Invoke from main graph node**:

```python
from polyplexity_agent.graphs.subgraphs.[subgraph] import [subgraph]_graph

def call_[subgraph]_node(state: SupervisorState):
    """Invokes the [subgraph name] subgraph."""
    # Map main graph state to subgraph state
    subgraph_state = {
        "[field1]": state.get("[main_field]"),
        "[field2]": state.get("[main_field2]"),
    }
    
    # Stream subgraph execution
    result_value = None
    for mode, data in [subgraph]_graph.stream(
        subgraph_state,
        stream_mode=["custom", "values"]
    ):
        if mode == "custom":
            # Forward events to main graph stream
            from langgraph.config import get_stream_writer
            writer = get_stream_writer()
            if writer:
                items = data if isinstance(data, list) else [data]
                for item in items:
                    writer(item)
        elif mode == "values":
            if "[result_field]" in data:
                result_value = data["[result_field]"]
    
    # Return updates to main graph state
    return {
        "[main_field]": result_value,
        "execution_trace": [trace_event]
    }
```

### Subgraph Export

Add to `graphs/subgraphs/__init__.py`:

```python
from .[subgraph] import create_[subgraph]_graph, [subgraph]_graph

__all__ = [
    # ... existing exports
    "create_[subgraph]_graph",
    "[subgraph]_graph",
]
```

## Adding a New Tool

### Template: Tool Implementation

```python
"""
[Tool name] tool implementation.

[Brief description of what the tool does]
"""
from typing import List, Dict, Any, Optional

# Tool-specific imports
import requests  # Example: for API calls


# Tool configuration constants
[TOOL]_API_URL = "https://api.example.com/endpoint"


def _helper_function(param: str) -> Dict[str, Any]:
    """
    Helper function for tool logic.
    
    Args:
        param: Parameter description
        
    Returns:
        Result dictionary
    """
    # Implementation here
    pass


def [tool_function_name](query: str) -> List[Dict[str, Any]]:
    """
    [Tool function description].
    
    Args:
        query: Search query or input parameter
        
    Returns:
        List of result dictionaries
        
    Raises:
        requests.RequestException: If API call fails
    """
    try:
        # Make API call or perform operation
        response = requests.get([TOOL]_API_URL, params={"q": query})
        response.raise_for_status()
        data = response.json()
        
        # Process and return results
        results = _process_results(data)
        return results
        
    except requests.RequestException as e:
        # Log error and re-raise
        raise
```

### Tool Location

Place tools in `tools/[tool_name].py`.

### Tool Usage in Nodes

```python
from polyplexity_agent.tools.[tool_name] import [tool_function_name]

def [node_name]_node(state: [StateType]):
    """Node that uses the tool."""
    query = state.get("[query_field]")
    
    # Call tool
    results = [tool_function_name](query)
    
    # Process results and return state updates
    return {
        "[result_field]": results,
        "execution_trace": [trace_event]
    }
```

### Tool Export

Add to `tools/__init__.py`:

```python
from .[tool_name] import [tool_function_name]

__all__ = [
    # ... existing exports
    "[tool_function_name]",
]
```

## Adding Streaming Events

### Event Envelope Format

All events must follow the standard envelope format:

```python
{
    "type": "custom|trace|state_update|system|error|complete",
    "timestamp": int,  # Milliseconds since epoch
    "node": "node_name",
    "event": "event_name",
    "payload": {
        # Event-specific data
    }
}
```

### Emitting Custom Events

```python
from polyplexity_agent.streaming import stream_custom_event

# Emit custom event from node
stream_custom_event(
    "event_name",           # Event name
    "node_name",            # Node that emits the event
    {"key": "value"}        # Event payload
)
```

### Emitting Trace Events

```python
from polyplexity_agent.streaming import stream_trace_event
from polyplexity_agent.streaming.event_serializers import create_trace_event

# Create trace event (for execution_trace field)
trace_event = create_trace_event(
    "trace_type",           # "node_call", "reasoning", "custom"
    "node_name",
    {"data": "value"}       # Trace data
)

# Emit trace event (for streaming)
stream_trace_event(
    "trace_type",
    "node_name",
    {"data": "value"}
)
```

### Event Types

- **`custom`**: Application-specific events (e.g., `supervisor_decision`, `web_search_url`)
- **`trace`**: Execution trace events (e.g., `node_call`, `reasoning`)
- **`state_update`**: State change notifications (auto-emitted by LangGraph)
- **`system`**: System-level events (e.g., `thread_id`, `thread_name`)
- **`error`**: Error events (emitted on exceptions)
- **`complete`**: Completion events (emitted when graph finishes)

### Forwarding Events from Subgraphs

When a subgraph emits events, forward them to the main graph stream:

```python
from langgraph.config import get_stream_writer

def call_subgraph_node(state: SupervisorState):
    """Node that invokes a subgraph."""
    for mode, data in subgraph_graph.stream(subgraph_state, stream_mode=["custom"]):
        if mode == "custom":
            writer = get_stream_writer()
            if writer:
                items = data if isinstance(data, list) else [data]
                for item in items:
                    writer(item)  # Forward to main graph stream
```

## Modifying State

### Adding New State Fields

**Step 1**: Update state TypedDict in `graphs/state.py`:

```python
class SupervisorState(TypedDict, total=False):
    # ... existing fields
    new_field: str  # Simple field
    new_list_field: Annotated[List[str], operator.add]  # Accumulating field
```

**Step 2**: Update nodes that use the field:

```python
def node_name(state: SupervisorState):
    return {
        "new_field": "value",
        "new_list_field": ["item"]  # Will accumulate if Annotated
    }
```

### State Accumulation

Use `Annotated[Type, reducer]` for fields that accumulate:

```python
from typing import Annotated
import operator

# Accumulate lists (concatenates)
research_notes: Annotated[List[str], operator.add]

# Custom reducer for structured data
conversation_history: Annotated[List[dict], manage_chat_history]
```

**Custom Reducer Example**:

```python
def custom_reducer(existing: List[dict], new: List[dict]) -> List[dict]:
    """Custom reducer that deduplicates and merges."""
    # Implementation
    return merged_list
```

### Backward Compatibility

When modifying state:

1. **Use `total=False`** in TypedDict to allow optional fields:
   ```python
   class SupervisorState(TypedDict, total=False):
       new_field: str  # Optional field
   ```

2. **Provide defaults** in nodes:
   ```python
   new_value = state.get("new_field", "default_value")
   ```

3. **Handle missing fields** gracefully:
   ```python
   if "new_field" in state:
       # Use new field
   else:
       # Fallback behavior
   ```

## Adding Configuration

### Adding Settings

**Step 1**: Update `config/settings.py`:

```python
class Settings(BaseSettings):
    # ... existing settings
    
    # New setting
    new_setting: str = "default_value"
    new_int_setting: int = 10
    
    # Optional: Environment variable support
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
```

**Step 2**: Use in code:

```python
from polyplexity_agent.config import Settings

settings = Settings()
value = settings.new_setting
```

### Adding Secrets

**Step 1**: Update `config/secrets.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

def get_new_api_key() -> Optional[str]:
    """
    Get API key from environment variable.
    
    Returns:
        API key string or None if not set
    """
    return os.getenv("NEW_API_KEY")
```

**Step 2**: Use in code:

```python
from polyplexity_agent.config.secrets import get_new_api_key

api_key = get_new_api_key()
if api_key:
    # Use API key
```

### Environment Variables

Add to `.env` file:

```bash
NEW_API_KEY=your_api_key_here
NEW_SETTING=value
```

## Import Patterns

### Package Imports

Always import from the installed package:

```python
from polyplexity_agent.config import Settings
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.streaming import stream_custom_event
```

### Relative Imports (Within Package)

Use relative imports within the package:

```python
# In graphs/nodes/supervisor/node.py
from ..state import SupervisorState
from ...streaming import stream_custom_event
```

### Circular Import Prevention

Use lazy imports for circular dependencies:

```python
# In node function (not at module level)
def node_name(state: SupervisorState):
    from polyplexity_agent.utils.state_manager import _state_logger
    # Use _state_logger
```

## Module Organization

### File Naming

- **Modules**: `snake_case.py` (e.g., `generate_queries.py`)
- **Classes**: `PascalCase` (e.g., `Settings`, `DatabaseManager`)
- **Functions**: `snake_case` (e.g., `create_agent_graph`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)

### Directory Structure

Follow the established structure:

```
polyplexity_agent/
├── config/          # Configuration
├── graphs/          # Graph definitions
│   ├── nodes/       # Node implementations
│   └── subgraphs/   # Subgraph definitions
├── streaming/      # Event handling
├── tools/           # External tools
├── prompts/         # LLM prompts
├── utils/           # Utilities
└── db_utils/        # Database utilities
```

### __init__.py Exports

Always export public APIs in `__init__.py`:

```python
# graphs/nodes/supervisor/__init__.py
from .supervisor import supervisor_node
from .final_report import final_report_node

__all__ = [
    "supervisor_node",
    "final_report_node",
]
```

## Code Style

Follow `CODING_STYLE.md`:

- **Function length**: ≤ 15 lines (excluding docstrings/comments)
- **Type hints**: Mandatory for all functions
- **Docstrings**: Google style with Args and Returns
- **Error handling**: Raise exceptions (don't log and re-raise)
- **String quotes**: Double quotes (`"`)
- **Line length**: 88 characters (Black formatting)

## Testing New Features

See `TESTING.md` for comprehensive testing guide. Key points:

1. **Unit tests**: Test node functions with mocked dependencies
2. **Integration tests**: Test subgraph execution end-to-end
3. **Mock external dependencies**: LLM calls, API calls, database
4. **Use fixtures**: Import from `conftest.py`
5. **Test edge cases**: Empty states, errors, max iterations

## Example: Complete Feature Addition

### Adding a "Fact Checker" Node

**1. Create node file** (`graphs/nodes/supervisor/fact_checker.py`):

```python
"""Fact checker node for the main agent graph."""
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.utils.helpers import log_node_state

def fact_checker_node(state: SupervisorState):
    """Fact-checks the final report."""
    from polyplexity_agent.utils.state_manager import _state_logger
    
    log_node_state(_state_logger, "fact_checker", "MAIN_GRAPH", dict(state), "BEFORE")
    
    report = state.get("final_report", "")
    # Fact-checking logic here
    
    stream_custom_event("fact_check_complete", "fact_checker", {"verified": True})
    
    return {"fact_checked": True}
```

**2. Add to graph** (`graphs/agent_graph.py`):

```python
from polyplexity_agent.graphs.nodes.supervisor.fact_checker import fact_checker_node

builder.add_node("fact_checker", fact_checker_node)
builder.add_edge("final_report", "fact_checker")
builder.add_edge("fact_checker", "summarize_conversation")
```

**3. Export** (`graphs/nodes/supervisor/__init__.py`):

```python
from .fact_checker import fact_checker_node
```

**4. Write tests** (`tests/graphs/nodes/supervisor/test_fact_checker.py`):

```python
def test_fact_checker_node(sample_supervisor_state):
    """Test fact checker node."""
    from polyplexity_agent.graphs.nodes.supervisor.fact_checker import fact_checker_node
    
    result = fact_checker_node(sample_supervisor_state)
    assert "fact_checked" in result
```

## Best Practices

1. **Keep nodes focused**: Each node should do one thing
2. **Emit events**: Use `stream_custom_event()` and `stream_trace_event()` for observability
3. **Log state**: Use `log_node_state()` for debugging
4. **Handle errors**: Emit error events before raising exceptions
5. **Type hints**: Always include type hints
6. **Docstrings**: Document all functions with Google-style docstrings
7. **Test thoroughly**: Write unit and integration tests
8. **Follow patterns**: Use existing nodes as templates
