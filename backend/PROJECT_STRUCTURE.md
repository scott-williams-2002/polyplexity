This document defines the **recommended structure, naming conventions, and architectural rules** for building a LangGraph-powered Python library.
This guides **Cursor**, contributors, and future-you to follow the same patterns everywhere.

**Note:**

> Not every file or folder listed here must exist in every project.
> What *is* required is following the **structure, patterns, naming conventions, and separation-of-concerns** defined in this document.

---

## 1. Folder Structure Overview

```
polyplexity_agent/
│
├── entrypoint.py
│
├── polyplexity/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── secrets.py
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── base_prompts.py
│   │
│   ├── graphs/
│   │   ├── __init__.py
│   │   ├── agent_graph.py
│   │   ├── state.py
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── search.py
│   │       ├── reasoning.py
│   │       └── post_processing.py
│   │
│   ├── streaming/
│   │   ├── __init__.py
│   │   ├── sse.py
│   │   ├── event_logger.py
│   │   └── event_serializers.py
│   │
│   ├── logging/
│   │   ├── __init__.py
│   │   └── logger.py
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── web_search.py
│   │   ├── retrieval.py
│   │   └── custom_api.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── timing.py
│       ├── decorators.py
│       └── formatting.py
│
├── tests/
│   ├── __init__.py
│   ├── test_graph.py
│   ├── test_nodes.py
│   ├── test_streaming.py
│   ├── test_prompts.py
│   └── fixtures/
│       └── sample_events.json
│
├── docs/
│   ├── PROJECT_STRUCTURE.md  (this file)
│   ├── API_REFERENCE.md
│   ├── ARCHITECTURE.md
│   └── CHANGELOG.md
│
├── pyproject.toml
└── README.md
```

---

# 2. Naming Conventions & Rules

### 📌 Files & Modules

| Type          | Convention         | Example             |
| ------------- | ------------------ | ------------------- |
| Modules       | `snake_case.py`    | `agent_graph.py`    |
| Classes       | `PascalCase`       | `EventLogger`       |
| Functions     | `snake_case`       | `build_graph()`     |
| Constants     | `UPPER_SNAKE_CASE` | `MAX_RETRIES`       |
| Private items | Prefix `_`         | `_internal_logic()` |

---

# 3. `entrypoint.py` — Main Entry Point

This is the **central “startup” module** of the whole library.
It **does not store graph logic**, but **exposes a small set of clearly-named helper functions** used to run an agent.

### Example responsibilities:

* Initialize global config
* Construct the LangGraph agent system
* Provide convenience `run_*` helpers
* Handle high-level orchestration

### Required structure:

```python
"""
entrypoint.py
Main entrypoint for initializing and running LangGraph agents.

Exposes high-level helper functions for easy importing:
    from entrypoint import run_agent, create_default_graph
"""

from typing import Any, Dict
from polyplexity_agent.graphs.agent_graph import create_agent_graph
from polyplexity_agent.config.settings import Settings


def create_default_graph() -> Any:
    """
    Construct and return the default agent graph.

    Returns:
        Any: A LangGraph graph instance.
    """
    settings = Settings()
    return create_agent_graph(settings=settings)


def run_agent(user_input: str) -> Dict[str, Any]:
    """
    Run the agent end-to-end on a single user input.

    Args:
        user_input (str): The prompt from the user.

    Returns:
        Dict[str, Any]: Final structured output from the graph execution.
    """
    graph = create_default_graph()
    return graph.invoke({"input": user_input})
```

### Rules:

* Must contain only *top-level orchestration functions*
* Must include docstrings + type hints
* No business logic allowed (goes to `/polyplexity_agent/...`)
* Should provide *import convenience* for external callers

---

# 4. `polyplexity_agent/prompts/` Rules

* A module for storing **structured prompt templates**
* Prompts must be organized into classes or constants
* Use **Jinja2-like format strings** or LangChain templates
* Docstrings must annotate:

  * *purpose*
  * *inputs*
  * *expected output structure*

---

# 5. Graph & Node Structure (`polyplexity_agent/graphs/`)

### Rules:

* `state.py` defines the **canonical state type** (TypedDict or Pydantic)
* `agent_graph.py` defines:

  * graph creation
  * node wiring
  * edges/transitions

### Node Rules:

* Every node is in `polyplexity_agent/graphs/nodes/<name>.py`
* Every node must follow:

  ```python
  async def node_name(state: State) -> StateUpdate:
      """Docstring describing the node's role, inputs, outputs."""
  ```
* Must include type references:

  ```python
  from typing import TypedDict
  from polyplexity_agent.graphs.state import AgentState, StateUpdate
  ```

---

# 6. Streaming & SSE (`polyplexity_agent/streaming/`)

LangGraph provides an event stream (SSE).
This folder centralizes **all streaming logic**, including:

* Event models
* Event serializers
* SSE emitter
* Event logger (writes to DB or file)

### Required files:

| File                   | Purpose                                    |
| ---------------------- | ------------------------------------------ |
| `sse.py`               | Handles SSE formatting and async streaming |
| `event_logger.py`      | Logs all intermediate agent events         |
| `event_serializers.py` | Converts graph events → JSON structures    |

### Rules:

* All SSE messages must adhere to a common envelope:

  ```json
  {
    "type": "state_update",
    "timestamp": "...",
    "payload": {...}
  }
  ```
* Streaming and logging must never live inside node files

---

# 7. Logging (`polyplexity_agent/logging/logger.py`)

### Rules:

* Must use `structlog`
* Must output machine-friendly logs
* Must expose a `get_logger(name: str)` function
* Never import logging config inside business logic

---

# 8. Tools (`polyplexity_agent/tools/`)

### Purpose:

Reusable external service adapters:

* Search API
* Retrieval DB
* Internal microservice calls

### Rules:

* Every tool must contain:

  * input dataclass
  * output dataclass
  * single `execute(...)` method
  * docstrings + type hints

---

# 9. Utils (`polyplexity_agent/utils/`)

Rules:

* Small helpers ONLY
* Must be pure functions
* No side effects
* Must be fully typed

---

# 10. Tests (`/tests/`)

### Rules:

* One test file per corresponding module
* Use PyTest exclusively
* Each test must:

  * test inputs/outputs
  * test state transition correctness
  * test streaming events (fixtures provided)
* Use fixtures for:

  * agent state samples
  * fake SSE events
  * mock tool results

---

# 11. Docstring & Type Rules

### Every function must include:

* Summary line
* Args table
* Returns explanation
* Raises (if any)
* Exact type hints

### Example:

```python
def run_step(input: str) -> Dict[str, Any]:
    """
    Run a single reasoning step.

    Args:
        input (str): User-supplied text.

    Returns:
        Dict[str, Any]: Structured, validated model output.
    """
```

---

# 12. Import Hygiene Rules

* Never use relative imports beyond one level
* Always import from root (`polyplexity_agent.*`)
* `entrypoint.py` exposes import shortcuts for external use

---

# 13. What You *Must* Follow vs Optional

### Mandatory:

* Folder names & purpose
* Naming conventions
* Node patterns
* Graph structure rules
* Streaming/logging separation
* Docstrings + typing
* Entry point architecture

### Optional:

* Individual files (your project may not need all tools or nodes)
* Exact test fixtures
* Exact choice of logger backend
* Prompts layout (as long as consistent)

---

If you'd like, I can generate **boilerplate files** for every folder in the structure, including docstring templates and type definitions.
