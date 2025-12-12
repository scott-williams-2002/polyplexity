# Backend Structure Refactor Migration Plan

## Overview
This plan outlines the migration of `polyplexity/backend/` to conform to `PROJECT_STRUCTURE.md`. The migration will be done in phases, starting with high-level structural changes to maintain functionality, then moving to granular file reorganization.

## Package Structure

### polyplexity_agent as Installable Package

The `polyplexity_agent` directory is a proper installable Python package that lives at `polyplexity/backend/polyplexity_agent/`. 

**Package Configuration**:
- `pyproject.toml` is located at `polyplexity_agent/pyproject.toml` (package root)
- Package name: `polyplexity-agent`
- Package is installed in editable mode for development

**Installation**:
Before running `main.py` or tests, the package must be installed:
```bash
cd polyplexity/backend/polyplexity_agent
pip install -e .
```

**Import Patterns**:
- `main.py` imports from installed package: `from polyplexity_agent import ...`
- Tests can import from installed package or local source (fallback pattern)
- Within package: Use relative imports or `from polyplexity_agent.module import ...`

**Directory Structure**:
```
polyplexity/backend/
├── main.py                    # FastAPI app - imports from installed polyplexity_agent
├── requirements.txt           # Application dependencies
├── pyproject.toml            # (Backend-level config, if needed)
├── polyplexity_agent/        # The installable package
│   ├── pyproject.toml        # Package configuration (package root)
│   ├── __init__.py
│   ├── config/
│   ├── graphs/
│   └── ...
└── tests/                    # Tests (can import from installed or local package)
```

## Prerequisites

Before starting the migration:

1. **Install polyplexity_agent package in editable mode**:
   ```bash
   cd polyplexity/backend/polyplexity_agent
   pip install -e .
   ```

2. **Verify installation**:
   ```bash
   python -c "from polyplexity_agent.config import Settings; print('Package installed correctly configured"
   ```

3. **Install application dependencies**:
   ```bash
   cd polyplexity/backend
   pip install -r requirements.txt
   ```

## Updated Target Structure

### Node Organization
Nodes will be organized by subgraph:
```
graphs/
├── nodes/
│   ├── researcher/
│   │   ├── __init__.py
│   │   ├── generate_queries.py
│   │   ├── perform_search.py
│   │   └── synthesize_research.py
│   ├── market_research/
│   │   ├── __init__.py
│   │   ├── generate_market_queries.py
│   │   ├── fetch_markets.py
│   │   ├── process_and_rank_markets.py
│   │   └── evaluate_markets.py
│   └── supervisor/  (or agent/ or main/)
│       ├── __init__.py
│       ├── supervisor.py
│       ├── call_researcher.py
│       ├── direct_answer.py
│       ├── clarification.py
│       ├── final_report.py
│       └── summarize_conversation.py
├── subgraphs/
│   ├── researcher.py
│   └── market_research.py
├── agent_graph.py
└── state.py
```

### Test Organization (Hybrid Approach)
Tests mirror the source structure but keep related tests together:
```
tests/
├── __init__.py
├── fixtures/
│   ├── sample_events.json
│   ├── sample_states.py
│   └── mock_responses.py
├── graphs/
│   ├── __init__.py
│   ├── test_agent_graph.py
│   ├── test_state.py
│   └── nodes/
│       ├── __init__.py
│       ├── researcher/
│       │   ├── __init__.py
│       │   ├── test_generate_queries.py
│       │   ├── test_perform_search.py
│       │   └── test_synthesize_research.py
│       ├── market_research/
│       │   ├── __init__.py
│       │   ├── test_generate_market_queries.py
│       │   ├── test_fetch_markets.py
│       │   ├── test_process_and_rank_markets.py
│       │   └── test_evaluate_markets.py
│       └── supervisor/
│           ├── __init__.py
│           ├── test_supervisor.py
│           ├── test_call_researcher.py
│           ├── test_direct_answer.py
│           ├── test_clarification.py
│           ├── test_final_report.py
│           └── test_summarize_conversation.py
├── subgraphs/
│   ├── test_researcher.py
│   └── test_market_research.py
├── streaming/
│   ├── test_sse.py
│   ├── test_event_logger.py
│   └── test_event_serializers.py
├── tools/
│   └── test_polymarket.py
├── config/
│   ├── test_settings.py
│   └── test_secrets.py
└── utils/
    ├── test_helpers.py
    └── test_state_logger.py
```

## Current vs Target Structure Analysis

### Current Structure Issues
- `main.py` at backend root (FastAPI app) - should be separate from graph entrypoint
- `orchestrator.py` contains graph logic - should be in `graphs/agent_graph.py`
- `states.py` at root - should be `graphs/state.py`
- Nodes scattered across multiple files (`orchestrator.py`, `researcher.py`, `market_nodes.py`, `summarizer.py`)
- SSE streaming logic embedded in `main.py` - should be in `streaming/` folder
- Missing `config/` folder for settings/secrets
- Missing `logging/logger.py` (using custom `state_logger.py` in utils)
- `execution_trace.py` at root - should be in `streaming/` or `utils/`
- `models.py` at root - should be organized better
- `testing/` folder - should be `tests/` at backend root
- No `entrypoint.py` for graph initialization
- Tests don't use pytest properly or have mocking

### Target Structure (from PROJECT_STRUCTURE.md + Updates)

**Package Structure** (`polyplexity_agent/`):
```
polyplexity_agent/              # Installable package root
├── pyproject.toml             # Package configuration
├── __init__.py
├── entrypoint.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── secrets.py
├── graphs/
│   ├── __init__.py
│   ├── agent_graph.py
│   ├── state.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── researcher/
│   │   ├── market_research/
│   │   └── supervisor/
│   └── subgraphs/
│       └── __init__.py
├── streaming/
│   ├── __init__.py
│   ├── sse.py
│   ├── event_logger.py
│   └── event_serializers.py
├── logging/
│   ├── __init__.py
│   └── logger.py
├── tools/
│   └── __init__.py
├── utils/
│   └── __init__.py
└── prompts/
    └── __init__.py
```

**Note**: All file paths in this document are relative to `polyplexity_agent/` package root unless otherwise specified.

## Migration Phases

### Phase 1: Foundation - Create New Structure (Non-Breaking)
**Goal**: Create new folders and placeholder files without breaking existing code.

**Tasks**:
1. Create `config/` folder with `__init__.py` (within `polyplexity_agent/` package)
2. Create `graphs/` folder with `__init__.py`
3. Create `graphs/nodes/` folder with `__init__.py`
4. Create `graphs/nodes/researcher/` folder with `__init__.py`
5. Create `graphs/nodes/market_research/` folder with `__init__.py`
6. Create `graphs/nodes/supervisor/` folder with `__init__.py`
7. Create `graphs/subgraphs/` folder with `__init__.py`
8. Create `streaming/` folder with `__init__.py`
9. Create `logging/` folder with `__init__.py`
10. Create `tests/` folder structure (at `polyplexity/backend/tests/`):
    - `tests/fixtures/`
    - `tests/graphs/nodes/researcher/`
    - `tests/graphs/nodes/market_research/`
    - `tests/graphs/nodes/supervisor/`
    - `tests/streaming/`
    - `tests/tools/`
    - `tests/config/`
    - `tests/utils/`

**Note**: All paths are relative to `polyplexity_agent/` package root. The package should be installed in editable mode (`pip install -e .`) before proceeding.

**Dependencies**: Package installation - `pip install -e .` from `polyplexity_agent/` directory

---

### Phase 2: Configuration Migration
**Goal**: Extract configuration logic into `config/` folder.

**Tasks**:
1. Create `config/settings.py`:
   - Extract model configuration from `orchestrator.py` (ChatGroq model, temperature, retries)
   - Extract state logs directory configuration
   - Create Settings class using Pydantic or dataclass
2. Create `config/secrets.py`:
   - Move database connection logic from `db_utils/db_config.py`
   - Handle environment variable loading
   - Keep secrets separate from settings
3. Update imports in files that use config (orchestrator.py, researcher.py, etc.)
4. Create `tests/config/test_settings.py` and `tests/config/test_secrets.py` with pytest mocks

**Files to Modify** (all within `polyplexity_agent/` package):
- `orchestrator.py` - remove hardcoded config, import from config
- `researcher.py` - remove hardcoded config, import from config
- `db_utils/db_config.py` - refactor to use config/secrets.py

**Files to Create**:
- `config/settings.py` (within package)
- `config/secrets.py` (within package)
- `config/__init__.py` (within package)
- `tests/config/test_settings.py` (at backend root)
- `tests/config/test_secrets.py` (at backend root)

**Import Pattern**: All imports use package imports: `from polyplexity_agent.config import Settings`

**Dependencies**: Phase 1 complete, package installed in editable mode

---

### Phase 3: State and Graph Structure Migration
**Goal**: Move state definitions and graph construction to proper locations.

**Tasks**:
1. Move `states.py` → `graphs/state.py`
   - Update all imports across codebase
   - Verify TypedDict definitions match target structure
2. Create `graphs/agent_graph.py`:
   - Extract graph building logic from `orchestrator.py`
   - Move `StateGraph` construction, node wiring, edges
   - Keep graph compilation logic here
   - Export `create_agent_graph(settings)` function
3. Create `entrypoint.py`:
   - Extract `run_research_agent()` function from `orchestrator.py`
   - Create `create_default_graph()` helper
   - Provide high-level API for external callers
   - Keep minimal orchestration logic
4. Create `tests/graphs/test_state.py` and `tests/graphs/test_agent_graph.py`

**Files to Modify**:
- `states.py` → `graphs/state.py` (move)
- `orchestrator.py` → split into `graphs/agent_graph.py` + `entrypoint.py`
- All files importing from `states.py` - update imports
- `__init__.py` - update exports

**Files to Create**:
- `graphs/state.py` (moved)
- `graphs/agent_graph.py`
- `graphs/__init__.py`
- `entrypoint.py`
- `tests/graphs/test_state.py`
- `tests/graphs/test_agent_graph.py`

**Dependencies**: Phase 2 complete

---

### Phase 4: Supervisor Node Migration
**Goal**: Move supervisor (main graph) nodes to `graphs/nodes/supervisor/`.

**Tasks**:
1. Extract nodes from `orchestrator.py` → `graphs/nodes/supervisor/`:
   - `supervisor_node` → `graphs/nodes/supervisor/supervisor.py`
   - `call_researcher_node` → `graphs/nodes/supervisor/call_researcher.py`
   - `direct_answer_node` → `graphs/nodes/supervisor/direct_answer.py`
   - `clarification_node` → `graphs/nodes/supervisor/clarification.py`
   - `final_report_node` → `graphs/nodes/supervisor/final_report.py`
   - Helper functions (`_make_supervisor_decision`, `_generate_final_report`, etc.) → move to respective node files or `utils/`
2. Extract nodes from `summarizer.py`:
   - `summarize_conversation_node` → `graphs/nodes/supervisor/summarize_conversation.py`
   - `manage_chat_history` → keep in same file or move to `utils/`
3. Update `graphs/agent_graph.py` to import from new node locations
4. Create test files for each node:
   - `tests/graphs/nodes/supervisor/test_supervisor.py`
   - `tests/graphs/nodes/supervisor/test_call_researcher.py`
   - `tests/graphs/nodes/supervisor/test_direct_answer.py`
   - `tests/graphs/nodes/supervisor/test_clarification.py`
   - `tests/graphs/nodes/supervisor/test_final_report.py`
   - `tests/graphs/nodes/supervisor/test_summarize_conversation.py`
   - Each test should use pytest fixtures and mocking

**Files to Create**:
- `graphs/nodes/supervisor/supervisor.py`
- `graphs/nodes/supervisor/call_researcher.py`
- `graphs/nodes/supervisor/direct_answer.py`
- `graphs/nodes/supervisor/clarification.py`
- `graphs/nodes/supervisor/final_report.py`
- `graphs/nodes/supervisor/summarize_conversation.py`
- `graphs/nodes/supervisor/__init__.py` (exports)
- All corresponding test files

**Files to Modify**:
- `orchestrator.py` - remove node implementations
- `summarizer.py` - remove node implementation
- `graphs/agent_graph.py` - update imports

**Dependencies**: Phase 3 complete

---

### Phase 5: Researcher Subgraph Migration
**Goal**: Move researcher subgraph and its nodes to proper locations.

**Tasks**:
1. Extract nodes from `researcher.py` → `graphs/nodes/researcher/`:
   - `generate_queries_node` → `graphs/nodes/researcher/generate_queries.py`
   - `perform_search_node` → `graphs/nodes/researcher/perform_search.py`
   - `synthesize_research_node` → `graphs/nodes/researcher/synthesize_research.py`
2. Move graph building logic:
   - `researcher.py` → `graphs/subgraphs/researcher.py`
   - Keep graph building logic in `graphs/subgraphs/researcher.py`
   - Export `create_researcher_graph()` function
3. Create test files:
   - `tests/graphs/nodes/researcher/test_generate_queries.py`
   - `tests/graphs/nodes/researcher/test_perform_search.py`
   - `tests/graphs/nodes/researcher/test_synthesize_research.py`
   - `tests/subgraphs/test_researcher.py` (integration test for subgraph)

**Files to Create**:
- `graphs/nodes/researcher/generate_queries.py`
- `graphs/nodes/researcher/perform_search.py`
- `graphs/nodes/researcher/synthesize_research.py`
- `graphs/nodes/researcher/__init__.py`
- `graphs/subgraphs/researcher.py` (refactored)
- `graphs/subgraphs/__init__.py`
- All corresponding test files

**Files to Modify**:
- `researcher.py` → refactor to `graphs/subgraphs/researcher.py`
- `graphs/nodes/supervisor/call_researcher.py` - update import for researcher graph

**Dependencies**: Phase 4 complete

---

### Phase 6: Market Research Subgraph Migration
**Goal**: Move market research subgraph and its nodes.

**Tasks**:
1. Extract nodes from `market_nodes.py` → `graphs/nodes/market_research/`:
   - `generate_market_queries_node` → `graphs/nodes/market_research/generate_market_queries.py`
   - `fetch_markets_node` → `graphs/nodes/market_research/fetch_markets.py`
   - `process_and_rank_markets_node` → `graphs/nodes/market_research/process_and_rank_markets.py`
   - `evaluate_markets_node` → `graphs/nodes/market_research/evaluate_markets.py`
2. Move graph building logic:
   - `market_subgraph.py` → `graphs/subgraphs/market_research.py`
   - Export `create_market_research_graph()` function
3. Delete `market_nodes.py` after migration
4. Create test files:
   - `tests/graphs/nodes/market_research/test_generate_market_queries.py`
   - `tests/graphs/nodes/market_research/test_fetch_markets.py`
   - `tests/graphs/nodes/market_research/test_process_and_rank_markets.py`
   - `tests/graphs/nodes/market_research/test_evaluate_markets.py`
   - `tests/subgraphs/test_market_research.py`

**Files to Create**:
- `graphs/nodes/market_research/generate_market_queries.py`
- `graphs/nodes/market_research/fetch_markets.py`
- `graphs/nodes/market_research/process_and_rank_markets.py`
- `graphs/nodes/market_research/evaluate_markets.py`
- `graphs/nodes/market_research/__init__.py`
- `graphs/subgraphs/market_research.py` (refactored)
- All corresponding test files

**Files to Modify**:
- `market_subgraph.py` → refactor to `graphs/subgraphs/market_research.py`
- `market_nodes.py` → delete after migration

**Dependencies**: Phase 5 complete

---

### Phase 7: Streaming Migration
**Goal**: Extract SSE and event handling to `streaming/` folder.

**Tasks**:
1. Create `streaming/event_serializers.py`:
   - Move `execution_trace.py` logic here or integrate it
   - Create serializers for different event types
   - Handle conversion of graph events → JSON structures
2. Create `streaming/event_logger.py`:
   - Move `utils/state_logger.py` logic here (or keep state_logger separate?)
   - Create event logging functionality
   - Handle writing events to DB or file
3. Create `streaming/sse.py`:
   - Extract SSE generator logic from `main.py`
   - Create SSE formatting functions
   - Handle async streaming
   - Implement common envelope format: `{"type": "...", "timestamp": "...", "payload": {...}}`
4. Update `main.py` to use streaming modules
5. Update `entrypoint.py` to integrate with streaming
6. Create test files:
   - `tests/streaming/test_sse.py` (with mocking for FastAPI StreamingResponse)
   - `tests/streaming/test_event_logger.py` (with mocking for file/DB writes)
   - `tests/streaming/test_event_serializers.py` (unit tests for serialization)

**Files to Create**:
- `streaming/event_serializers.py`
- `streaming/event_logger.py`
- `streaming/sse.py`
- `streaming/__init__.py` (exports)
- All corresponding test files

**Files to Modify**:
- `main.py` - use streaming modules
- `execution_trace.py` - decide: merge into streaming or keep separate?
- `utils/state_logger.py` - decide: move to streaming or keep in utils?

**Dependencies**: Phase 3 complete (needs graph structure)

---

### Phase 8: Logging Migration
**Goal**: Implement structured logging per PROJECT_STRUCTURE.md.

**Tasks**:
1. Create `logging/logger.py`:
   - Implement using `structlog`
   - Create `get_logger(name: str)` function
   - Output machine-friendly logs
   - Replace or wrap existing `state_logger.py` functionality
2. Update all files to use new logger:
   - Replace print statements with logger calls
   - Update `utils/state_logger.py` to use structlog if keeping it
   - Update nodes to use logger
3. Create `tests/logging/test_logger.py` with pytest mocks

**Files to Create**:
- `logging/logger.py`
- `logging/__init__.py` (exports)
- `tests/logging/test_logger.py`

**Files to Modify**:
- All files with print statements or logging
- `utils/state_logger.py` (if keeping)

**Dependencies**: Can be done in parallel with other phases

---

### Phase 9: Models and Utils Cleanup
**Goal**: Organize models and utilities properly.

**Tasks**:
1. Decide on `models.py` location:
   - **Recommendation**: Keep at root or move to `utils/` since they're used across modules
2. Review `utils/helpers.py`:
   - Ensure all functions are pure helpers
   - Move any business logic out
   - Verify type hints and docstrings
3. Review `utils/state_logger.py`:
   - Decide if this stays in utils or moves to streaming/logging
   - **Recommendation**: Keep in utils if it's file-based logging, move to logging/ if it's general logging
4. Create test files:
   - `tests/utils/test_helpers.py` (with pytest mocks)
   - `tests/utils/test_state_logger.py` (if keeping)

**Files to Modify**:
- `models.py` - potentially move
- `utils/helpers.py` - cleanup
- `utils/state_logger.py` - decide location

**Files to Create**:
- Test files for utils

**Dependencies**: Phase 6, 7, 8 complete

---

### Phase 10: Testing Infrastructure Setup
**Goal**: Set up proper pytest infrastructure with fixtures and mocking.

**Tasks**:
1. Create `tests/conftest.py`:
   - Define pytest fixtures for:
     - Mock LLM responses
     - Sample state dictionaries
     - Mock database connections
     - Mock streaming writers
     - Sample execution traces
2. Create `tests/fixtures/` folder:
   - `sample_events.json` - sample SSE events
   - `sample_states.py` - TypedDict state samples
   - `mock_responses.py` - Mock LLM/tool responses
3. Update `pyproject.toml` or `pytest.ini`:
   - Configure pytest
   - Add pytest-mock, pytest-asyncio if needed
   - Set test discovery patterns
4. Create example test files showing patterns:
   - How to mock LLM calls
   - How to test node functions
   - How to test state transitions
   - How to test streaming events

**Files to Create**:
- `tests/conftest.py`
- `tests/fixtures/sample_events.json`
- `tests/fixtures/sample_states.py`
- `tests/fixtures/mock_responses.py`
- Update pytest configuration

**Dependencies**: Can be done early, but needs to be finalized before Phase 11

---

### Phase 11: Import Updates and Cleanup
**Goal**: Update all imports and remove old files.

**Tasks**:
1. Update `__init__.py` files:
   - `polyplexity_agent/__init__.py` - export from entrypoint, graphs, etc.
   - `graphs/__init__.py` - export graph creation functions
   - `graphs/nodes/__init__.py` - export all nodes (or organize by subgraph)
   - `graphs/nodes/researcher/__init__.py` - export researcher nodes
   - `graphs/nodes/market_research/__init__.py` - export market nodes
   - `graphs/nodes/supervisor/__init__.py` - export supervisor nodes
   - `streaming/__init__.py` - export streaming functions
   - `config/__init__.py` - export Settings
   - `logging/__init__.py` - export get_logger
2. Update `main.py`:
   - Import from new locations
   - Use new streaming modules
   - Use new entrypoint functions
3. Remove old files:
   - `orchestrator.py` (after migration)
   - `market_nodes.py` (after migration)
   - `researcher.py` (after migration to subgraphs)
   - `summarizer.py` (after node migration)
   - `execution_trace.py` (if merged into streaming)
4. Update all import statements across codebase
5. Verify no broken imports
6. Run all tests to ensure nothing broke

**Files to Modify**:
- All Python files with imports
- All `__init__.py` files

**Files to Delete**:
- `orchestrator.py`
- `market_nodes.py`
- `researcher.py` (original)
- `summarizer.py`
- `execution_trace.py` (if merged)

**Dependencies**: All previous phases

---

### Phase 12: Documentation and Finalization
**Goal**: Update documentation and verify structure compliance.

**Tasks**:
1. Update `PROJECT_STRUCTURE.md` if needed (add notes about db_utils, FastAPI main.py, node organization)
2. Create migration notes document
3. Verify all files follow naming conventions:
   - Modules: `snake_case.py`
   - Classes: `PascalCase`
   - Functions: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
4. Verify docstrings and type hints per PROJECT_STRUCTURE.md
5. Run full test suite:
   - Unit tests for all nodes
   - Integration tests for subgraphs
   - Integration tests for main graph
   - Streaming tests
   - Tool tests
6. Update README if needed
7. Document test patterns and conventions

**Dependencies**: Phase 11 complete

---

## Key Decisions Made

1. **Database utilities**: Keep `db_utils/` folder as-is (domain-specific, not in generic structure)
2. **main.py vs entrypoint.py**: Split - keep `main.py` for FastAPI, create `entrypoint.py` for graph initialization
3. **Subgraphs**: Move to `graphs/subgraphs/` folder
4. **Node organization**: Nodes organized by subgraph in `graphs/nodes/<subgraph_name>/`
5. **Test structure**: Hybrid approach - mirror source structure but keep related tests together
6. **Testing**: Use pytest with mocking, fixtures in `tests/fixtures/`
7. **execution_trace.py**: Merge into `streaming/event_serializers.py` or keep separate - needs decision
8. **state_logger.py**: Keep in utils or move to logging - needs decision based on usage

## Risk Areas

1. **Import chains**: Many files import from each other - need careful dependency ordering
2. **Graph compilation**: Moving graph building logic could break if not done carefully
3. **Streaming**: SSE logic is tightly coupled with main.py - need clean separation
4. **State management**: Moving states.py will require updating many imports
5. **Testing**: Tests will break during migration - need to update incrementally
6. **Node dependencies**: Nodes call each other and subgraphs - need to maintain import paths

## Testing Strategy

- After each phase, run existing tests
- Update test imports incrementally
- Create tests as you migrate (test-driven migration)
- Use pytest fixtures for common test data
- Mock external dependencies (LLM, database, APIs)
- Verify FastAPI endpoints still work
- Verify graph execution still works
- Verify streaming still works

## Test Patterns to Follow

### Node Test Pattern
```python
import pytest
from unittest.mock import Mock, patch

# Import from installed package (or local source as fallback)
try:
    from polyplexity_agent.graphs.state import SupervisorState
    from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node
except ImportError:
    # Fallback to local source if package not installed
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "polyplexity_agent"))
    from graphs.state import SupervisorState
    from graphs.nodes.supervisor.supervisor import supervisor_node

@pytest.fixture
def sample_state():
    return {
        "user_request": "Test question",
        "research_notes": [],
        "iterations": 0,
        # ... other required fields
    }

@patch('polyplexity_agent.graphs.nodes.supervisor.supervisor.create_llm_model')
def test_supervisor_node(mock_llm, sample_state):
    # Mock LLM response
    mock_llm.return_value.with_structured_output.return_value.invoke.return_value = Mock(
        next_step="research",
        research_topic="test topic",
        reasoning="test reasoning"
    )
    
    # Mock stream writer
    with patch('langgraph.config.get_stream_writer') as mock_writer:
        result = supervisor_node(sample_state)
        
        # Assertions
        assert "next_topic" in result
        assert result["next_topic"] == "test topic"
```

### Subgraph Test Pattern
```python
import pytest
from polyplexity_agent.graphs.subgraphs.researcher import create_researcher_graph

def test_researcher_subgraph():
    graph = create_researcher_graph()
    initial_state = {"topic": "test", "query_breadth": 3}
    
    # Test graph execution
    result = graph.invoke(initial_state)
    assert "research_summary" in result
```

## Estimated File Moves/Creates

- **New folders**: 8+ (config, graphs, graphs/nodes/*, graphs/subgraphs, streaming, logging, tests/*)
- **Files to move**: ~15
- **Files to create**: ~40+ (including test files)
- **Files to delete**: ~5
- **Files to modify**: ~30+

## Next Steps

1. Start with Phase 1 (foundation) - create folder structure
2. Then proceed phase by phase, testing after each
3. Create separate planning sessions for complex phases (e.g., Phase 4-6 for nodes)
4. Document any deviations from PROJECT_STRUCTURE.md
5. Set up pytest infrastructure early (Phase 10 can start early)
