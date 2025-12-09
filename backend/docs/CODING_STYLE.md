# Backend Coding Style Guide

This document outlines the coding standards and best practices for the backend of the Polyplexity application. Adherence to these guidelines ensures codebase consistency, readability, and maintainability.

## Quick Reference

| Feature | Rule | Context/Example |
| :--- | :--- | :--- |
| **New Function/Node** | **≤ 15 Lines of Code** | Strict limit. Extract logic to helpers if needed. |
| **Type Hinting** | **Mandatory** | Use `typing` module (e.g., `List`, `Optional`, `Dict`). |
| **Docstrings** | **Google Style** | Must include `Args:` and `Returns:` sections. |
| **Error Handling** | **Raise Only** | Do not log & re-raise. Let global handlers manage logging. |
| **Database** | **ORMs Allowed** | Raw SQL (psycopg) or ORMs (SQLAlchemy) are permitted. |
| **String Quotes** | **Double Quotes (`"`)** | Use double quotes for all string literals. |
| **Line Length** | **88 Characters** | Follows strict Black formatting rules. |

---

## 1. General Formatting

We enforce a consistent code style to minimize cognitive load when reading code.

-   **Line Length:** Maximum **88 characters** (standard Black configuration).
-   **Indentation:** Use **4 spaces** per indentation level. No tabs.
-   **Quotes:** Use **double quotes** (`"string"`) for all string literals, unless the string contains double quotes (e.g., `'He said "Hello"'`).
-   **Imports:** Organize imports as follows, separated by a single blank line between each group:
    1.  **Standard library imports** (e.g., `os`, `sys`, `json`, `datetime`, `typing` module)
    2.  **Third-party library imports** (e.g., `requests`, `langgraph`, `sqlalchemy`, `fastapi`, `pydantic`)
    3.  **Local application imports** (modules from our own codebase, e.g., `db_utils`, `agent.orchestrator`)

    ```python
    import os
    from datetime import datetime
    from typing import List, Optional

    import requests
    from langgraph.graph import StateGraph
    from sqlalchemy.orm import Session

    from db_utils import get_database_manager
    from agent.orchestrator import run_research_agent
    ```

## 2. Python & Typing

### 2.1 Function Length (Strict)
**Rule:** All functions, including graph nodes and helper functions, must be **≤ 15 lines of code**.
-   This count excludes docstrings and comments.
-   **Why?** Forces modularity, readability, and easier testing.
-   **How?** If a function grows too large, extract logical blocks into helper functions in `utils/` or private `_helper` functions.

### 2.2 Type Hinting
**Rule:** Type hinting is **mandatory** for all function arguments and return values.
-   Use the `typing` module for complex types.
-   **Preferred:** `List[str]`, `Dict[str, Any]`, `Optional[int]`.
-   **Avoid:** `list[str]` (modern syntax) unless python version strictly mandated, for consistency with existing codebase patterns using `typing`.

```python
from typing import List, Dict, Optional

def process_data(items: List[str], config: Dict[str, str]) -> Optional[int]:
    # ... implementation ...
    pass
```

### 2.3 Docstrings
**Rule:** All modules, classes, and functions must have docstrings using the **Google Style**.
-   **Description:** A concise summary of what the code does.
-   **Args:** detailed description of arguments.
-   **Returns:** description of the return value.
-   **Raises:** (Optional) List of errors raised.

```python
def calculate_metrics(data: List[float]) -> float:
    """
    Calculates the average metric from the provided data points.

    Args:
        data: A list of floating-point numbers representing raw metrics.

    Returns:
        The calculated average as a float.
    """
    # ...
```

### 2.4 Variable Naming
-   **Variables/Functions:** `snake_case` (e.g., `user_id`, `calculate_total`).
-   **Classes:** `PascalCase` (e.g., `ResearchAgent`, `Checkpointer`).
-   **Constants:** `UPPER_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`).

## 3. Architecture

### 3.1 File Structure
Maintain a strict separation of concerns:
-   **`agent/`**: Core logic for LangGraph agents.
-   **`prompts/`**: All LLM prompts. **Never** hardcode prompts inside logic files.
-   **`utils/`**: Helper functions and shared utilities.
-   **`models/`**: Pydantic models for structured data.

### 3.2 Database Access
-   **Tooling:** Both raw SQL (using `psycopg`) and ORMs (like SQLAlchemy or SQLModel) are permitted.
-   **Pattern:** Isolate database queries into dedicated repository functions or utility modules (e.g., `utils/message_store.py`). Do not scatter SQL queries throughout business logic.

## 4. Error Handling

**Rule:** **Raise exceptions** rather than catching and logging them locally, unless you are at the top-level entry point (like an API endpoint or a background worker root).
-   **Don't:** `try: ... except Exception as e: print(e); raise e` (Noise).
-   **Do:** Let the exception bubble up to the global exception handler in FastAPI or the main execution loop, which handles standardized logging and error reporting.

## 5. Tooling & Enforcement

Code quality is enforced using the following tools:
-   **Formatter:** **Black** (Line length 88).
-   **Linter:** **Flake8** (PEP 8 compliance).
-   **Type Checker:** **Mypy** (Optional but recommended for critical paths).

---
*Reference this guide when reviewing PRs or adding new features.*

