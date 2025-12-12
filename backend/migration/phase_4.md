# Phase 4: Supervisor Node Migration - Implementation Summary

## Plan Overview

**Goal**: Extract all supervisor node functions from `orchestrator.py` and `summarizer.py` into organized node files in `graphs/nodes/supervisor/`. Each node will be in its own file with its helper functions. Update imports across the codebase and create comprehensive test files.

**Status**: ✅ **COMPLETED**

## Package Context

**Important**: All changes in Phase 4 are within the `polyplexity_agent` installable package located at `polyplexity/backend/polyplexity_agent/`.

- **Package Structure**: `polyplexity_agent` is an installable Python package
- **Package Root**: `polyplexity_agent/pyproject.toml` contains package configuration
- **Installation**: Package must be installed in editable mode: `cd polyplexity_agent && pip install -e .`
- **Import Pattern**: All imports use package imports: `from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node`
- **File Paths**: All paths in this document are relative to `polyplexity_agent/` package root

---

## Implementation Steps Completed

### 1. Extracted Supervisor Nodes from orchestrator.py ✅

#### 1.1 Created `graphs/nodes/supervisor/supervisor.py` ✅

Extracted `supervisor_node()` function and its helper functions:

- **Node Function**: `supervisor_node(state: SupervisorState)`
  - Decides whether to research more, finish, or ask for clarification
  - Handles iteration limits (max 10 iterations hard limit)
  - Generates thread name on first iteration
  - Makes supervisor decision using LLM
  - Emits trace events and logs state

- **Helper Functions Moved**:
  - `_make_supervisor_decision()` - Makes supervisor decision using LLM with structured output
  - `_emit_supervisor_trace_events()` - Emits supervisor trace events to stream writer
  - `_handle_thread_name_generation()` - Generates and saves thread name on first iteration

- **Dependencies**:
  - Imports `SupervisorState` from `graphs.state`
  - Imports `Settings` from `config`
  - Imports `SupervisorDecision` from `models`
  - Imports helper functions from `utils.helpers`
  - Imports prompts from `prompts.supervisor`
  - Accesses `_state_logger` from `orchestrator` module (temporary until Phase 8)

#### 1.2 Created `graphs/nodes/supervisor/call_researcher.py` ✅

Extracted `call_researcher_node()` function:

- **Node Function**: `call_researcher_node(state: SupervisorState)`
  - Invokes the researcher subgraph with the current research topic
  - Determines query breadth based on answer format (3 for concise, 5 for report)
  - Streams subgraph execution and forwards custom events
  - Deduplicates `web_search_url` events by URL
  - Captures research summary and formats as note

- **Dependencies**:
  - Imports `researcher_graph` from `researcher`
  - Imports `SupervisorState` from `graphs.state`
  - Accesses `_state_logger` from `orchestrator` module (temporary)

#### 1.3 Created `graphs/nodes/supervisor/direct_answer.py` ✅

Extracted `direct_answer_node()` function and helper:

- **Node Function**: `direct_answer_node(state: SupervisorState)`
  - Answers simple questions directly without research
  - Uses conversation summary for context

- **Helper Function**: `_handle_direct_answer()`
  - Generates direct answer using LLM
  - Emits trace events
  - Saves messages and trace to database
  - Returns updated state with final report and conversation history

- **Dependencies**:
  - Imports prompts from `prompts.response_generator`
  - Imports helper functions from `utils.helpers`

#### 1.4 Created `graphs/nodes/supervisor/clarification.py` ✅

Extracted `clarification_node()` function and helper:

- **Node Function**: `clarification_node(state: SupervisorState)`
  - Asks the user for clarification when the request is ambiguous
  - Extracts clarification question from `next_topic` if it starts with "CLARIFY:"

- **Helper Function**: `_handle_clarification()`
  - Generates clarification question
  - Emits trace events
  - Saves messages and trace to database
  - Returns updated state with clarification question

#### 1.5 Created `graphs/nodes/supervisor/final_report.py` ✅

Extracted `final_report_node()` function and helper:

- **Node Function**: `final_report_node(state: SupervisorState)`
  - Writes the final answer/report based on accumulated research notes
  - Handles both new reports and report refinements
  - Supports both concise and report formats

- **Helper Function**: `_generate_final_report()`
  - Generates final report using LLM
  - Uses different prompts for refinement vs new report
  - Uses different format instructions for concise vs report format
  - Returns generated report content

- **Dependencies**:
  - Imports prompts from `prompts.response_generator`
  - Imports helper functions from `utils.helpers`

### 2. Extracted Node from summarizer.py ✅

#### 2.1 Created `graphs/nodes/supervisor/summarize_conversation.py` ✅

Extracted `summarize_conversation_node()` function and helpers:

- **Node Function**: `summarize_conversation_node(state: Dict[str, Any])`
  - Summarizes conversation history and prunes the raw history
  - Formats history for summarization
  - Generates updated summary using LLM
  - Resets conversation history after summarization

- **Helper Functions**:
  - `_format_history_for_summary()` - Formats conversation history for the summarizer prompt
  - `_generate_summary()` - Generates the updated summary using the LLM

- **Reducer Function**: `manage_chat_history()`
  - Custom reducer for `conversation_history` field in `SupervisorState`
  - Checks for reset signal (type="reset") to replace history
  - Appends new messages
  - Enforces hard safety limit (keeps last 50 messages)
  - Kept in same file as per user decision

- **Dependencies**:
  - Imports from `prompts.system_prompts`
  - Imports helper functions from `utils.helpers`

### 3. Updated `graphs/agent_graph.py` ✅

Updated imports and moved routing function:

- **Updated Imports**:
  - Changed from importing nodes from `orchestrator`
  - To importing from new node locations:
    ```python
    from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node
    from polyplexity_agent.graphs.nodes.supervisor.call_researcher import call_researcher_node
    from polyplexity_agent.graphs.nodes.supervisor.direct_answer import direct_answer_node
    from polyplexity_agent.graphs.nodes.supervisor.clarification import clarification_node
    from polyplexity_agent.graphs.nodes.supervisor.final_report import final_report_node
    from polyplexity_agent.graphs.nodes.supervisor.summarize_conversation import summarize_conversation_node
    ```

- **Moved Function**: `route_supervisor()`
  - Moved from `orchestrator.py` to `agent_graph.py` (as per user decision)
  - Routes based on `next_topic` and `answer_format` constraints
  - Handles CLARIFY: prefix, FINISH state, and iteration limits
  - Returns routing decision: "clarification", "final_report", "direct_answer", or "call_researcher"

### 4. Updated `graphs/nodes/supervisor/__init__.py` ✅

Updated to export all node functions with lazy imports:

- **Exports Added**:
  - `supervisor_node`
  - `call_researcher_node`
  - `direct_answer_node`
  - `clarification_node`
  - `final_report_node`
  - `summarize_conversation_node`
  - `manage_chat_history`

- **Lazy Import Pattern**:
  - `manage_chat_history` and `summarize_conversation_node` imported eagerly (needed by `state.py`)
  - Other nodes imported lazily via `__getattr__()` to avoid circular dependencies
  - This prevents circular import: `state.py` → `summarize_conversation` → `supervisor/__init__.py` → `call_researcher` → `state.py`

### 5. Updated `graphs/state.py` ✅

Updated import for `manage_chat_history`:

- **Import Changed**:
  - From: `from polyplexity_agent.summarizer import manage_chat_history`
  - To: `from polyplexity_agent.graphs.nodes.supervisor.summarize_conversation import manage_chat_history`

- **Note**: This import must happen before other supervisor nodes are imported to avoid circular dependencies

### 6. Cleaned Up `orchestrator.py` ✅

Removed migrated functions and kept temporary infrastructure:

- **Removed**:
  - All node function definitions (moved to supervisor nodes)
  - `route_supervisor()` function (moved to `agent_graph.py`)
  - All helper functions (moved to respective node files)
  - Unused imports (prompts, models, etc.)

- **Kept Temporarily** (will be refactored in later phases):
  - `_state_logger` global variable
  - `set_state_logger()` function
  - `_checkpointer` global variable
  - `ensure_checkpointer_setup()` function
  - `main_graph` lazy initialization (for backward compatibility)

- **File Size Reduction**: From 475 lines to 68 lines (86% reduction)

### 7. Created Comprehensive Test Files ✅

Created test files following pytest patterns with fixtures and mocking:

#### 7.1 `tests/graphs/nodes/supervisor/test_supervisor.py` ✅

- **5 Test Functions**:
  - `test_supervisor_node_research_decision` - Tests research decision path
  - `test_supervisor_node_finish_decision` - Tests finish decision path
  - `test_supervisor_node_clarify_decision` - Tests clarify decision path
  - `test_supervisor_node_thread_name_generation` - Tests thread name generation
  - `test_supervisor_node_max_iterations` - Tests iteration limit enforcement

- **Mocking**: LLM calls, stream writer, state logger, trace events

#### 7.2 `tests/graphs/nodes/supervisor/test_call_researcher.py` ✅

- **4 Test Functions**:
  - `test_call_researcher_node` - Tests basic researcher invocation
  - `test_call_researcher_node_url_deduplication` - Tests URL deduplication
  - `test_call_researcher_node_breadth_concise` - Tests concise format breadth (3)
  - `test_call_researcher_node_breadth_report` - Tests report format breadth (5)

- **Mocking**: Researcher graph stream, stream writer, state logger

#### 7.3 `tests/graphs/nodes/supervisor/test_direct_answer.py` ✅

- **2 Test Functions**:
  - `test_direct_answer_node` - Tests direct answer generation
  - `test_direct_answer_node_saves_trace` - Tests trace saving

- **Mocking**: LLM calls, database operations, stream writer

#### 7.4 `tests/graphs/nodes/supervisor/test_clarification.py` ✅

- **2 Test Functions**:
  - `test_clarification_node` - Tests clarification with CLARIFY: prefix
  - `test_clarification_node_default_question` - Tests default clarification question

- **Mocking**: Stream writer, database operations

#### 7.5 `tests/graphs/nodes/supervisor/test_final_report.py` ✅

- **3 Test Functions**:
  - `test_final_report_node` - Tests basic report generation
  - `test_final_report_node_refinement` - Tests report refinement path
  - `test_final_report_node_report_format` - Tests report format instructions

- **Mocking**: LLM calls, database operations, stream writer

#### 7.6 `tests/graphs/nodes/supervisor/test_summarize_conversation.py` ✅

- **6 Test Functions**:
  - `test_manage_chat_history_append` - Tests message appending
  - `test_manage_chat_history_reset` - Tests reset signal handling
  - `test_manage_chat_history_limit` - Tests 50 message limit
  - `test_summarize_conversation_node` - Tests summary generation
  - `test_summarize_conversation_node_empty_history` - Tests empty history handling
  - `test_summarize_conversation_node_formats_history` - Tests history formatting

- **Mocking**: LLM calls for summary generation

---

## Files Created

**Source files (`polyplexity_agent/graphs/nodes/supervisor/`)**:
1. `supervisor.py` - supervisor_node + helpers (_make_supervisor_decision, _emit_supervisor_trace_events, _handle_thread_name_generation)
2. `call_researcher.py` - call_researcher_node
3. `direct_answer.py` - direct_answer_node + _handle_direct_answer helper
4. `clarification.py` - clarification_node + _handle_clarification helper
5. `final_report.py` - final_report_node + _generate_final_report helper
6. `summarize_conversation.py` - summarize_conversation_node + helpers + manage_chat_history reducer

**Test files (`tests/graphs/nodes/supervisor/`)**:
7. `test_supervisor.py` - 5 tests for supervisor_node
8. `test_call_researcher.py` - 4 tests for call_researcher_node
9. `test_direct_answer.py` - 2 tests for direct_answer_node
10. `test_clarification.py` - 2 tests for clarification_node
11. `test_final_report.py` - 3 tests for final_report_node
12. `test_summarize_conversation.py` - 6 tests for summarize_conversation_node and manage_chat_history

## Files Modified

**Within `polyplexity_agent/` package**:
1. `graphs/agent_graph.py` - Updated imports, added route_supervisor function
2. `graphs/nodes/supervisor/__init__.py` - Added exports with lazy import pattern
3. `graphs/state.py` - Updated manage_chat_history import
4. `orchestrator.py` - Removed migrated node functions and route_supervisor (86% reduction in file size)

---

## Debugging Process

### Issue 1: Circular Import Error
**Problem**: Tests failed with `ImportError: cannot import name 'SupervisorState' from partially initialized module 'polyplexity_agent.graphs.state'`

**Root Cause**:
- Circular dependency chain:
  1. `graphs/state.py` imports `manage_chat_history` from `summarize_conversation`
  2. `graphs/nodes/supervisor/__init__.py` imports all nodes including `call_researcher`
  3. `call_researcher.py` imports `SupervisorState` from `graphs.state`
  4. This creates a circular import when `state.py` is still initializing

**Solution**:
- Made imports in `graphs/nodes/supervisor/__init__.py` lazy using `__getattr__()` pattern
- Only `manage_chat_history` and `summarize_conversation_node` are imported eagerly (needed by `state.py`)
- All other nodes are imported lazily on-demand
- This breaks the circular dependency because `state.py` can import `manage_chat_history` without triggering import of other nodes

**Code Change**:
```python
# Before (graphs/nodes/supervisor/__init__.py):
from polyplexity_agent.graphs.nodes.supervisor.call_researcher import call_researcher_node
# ... all other imports

# After (graphs/nodes/supervisor/__init__.py):
# Only summarize_conversation imported eagerly
from polyplexity_agent.graphs.nodes.supervisor.summarize_conversation import (
    manage_chat_history,
    summarize_conversation_node,
)

def __getattr__(name: str):
    """Lazy import of supervisor nodes to avoid circular dependencies."""
    if name == "call_researcher_node":
        from polyplexity_agent.graphs.nodes.supervisor.call_researcher import call_researcher_node
        return call_researcher_node
    # ... other lazy imports
```

### Issue 2: Test Import Paths
**Problem**: Tests were patching `_state_logger` from wrong module path

**Root Cause**:
- Nodes import `_state_logger` from `orchestrator` module
- Tests were trying to patch `_state_logger` in the node modules themselves

**Solution**:
- Updated all test files to patch `polyplexity_agent.orchestrator._state_logger` instead of node-specific paths
- This correctly mocks the global logger that nodes access

**Code Change**:
```python
# Before (test files):
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor._state_logger")

# After (test files):
@patch("polyplexity_agent.orchestrator._state_logger")
```

---

## Testing

### Running Tests

**Activate virtual environment**:
```bash
cd /Users/scottwilliams/Desktop/tenex_application/polyplexity/backend
source .venv/bin/activate
```

**Install package and dependencies**:
```bash
# Install polyplexity_agent package in editable mode
cd polyplexity_agent
pip install -e .

# Install application dependencies
cd ..
pip install -r requirements.txt
```

**Run tests**:
```bash
# Run all supervisor node tests
pytest tests/graphs/nodes/supervisor/ -vv

# Run specific test file
pytest tests/graphs/nodes/supervisor/test_supervisor.py -vv

# Run all tests to verify no regressions
pytest tests/ -v
```

### Test Results

**Phase 4 Supervisor Node Tests** (all passing):
- ✅ `test_supervisor_node_research_decision` - Verifies research decision path
- ✅ `test_supervisor_node_finish_decision` - Verifies finish decision path
- ✅ `test_supervisor_node_clarify_decision` - Verifies clarify decision path
- ✅ `test_supervisor_node_thread_name_generation` - Verifies thread name generation
- ✅ `test_supervisor_node_max_iterations` - Verifies iteration limit enforcement
- ✅ `test_call_researcher_node` - Verifies researcher invocation
- ✅ `test_call_researcher_node_url_deduplication` - Verifies URL deduplication
- ✅ `test_call_researcher_node_breadth_concise` - Verifies concise format breadth
- ✅ `test_call_researcher_node_breadth_report` - Verifies report format breadth
- ✅ `test_clarification_node` - Verifies clarification with CLARIFY: prefix
- ✅ `test_clarification_node_default_question` - Verifies default question
- ✅ `test_direct_answer_node` - Verifies direct answer generation
- ✅ `test_direct_answer_node_saves_trace` - Verifies trace saving
- ✅ `test_final_report_node` - Verifies report generation
- ✅ `test_final_report_node_refinement` - Verifies report refinement
- ✅ `test_final_report_node_report_format` - Verifies format instructions
- ✅ `test_manage_chat_history_append` - Verifies message appending
- ✅ `test_manage_chat_history_reset` - Verifies reset signal handling
- ✅ `test_manage_chat_history_limit` - Verifies 50 message limit
- ✅ `test_summarize_conversation_node` - Verifies summary generation
- ✅ `test_summarize_conversation_node_empty_history` - Verifies empty history handling
- ✅ `test_summarize_conversation_node_formats_history` - Verifies history formatting

**All Tests**:
- ✅ 43 tests passed, 1 skipped (as expected)
- ✅ All existing tests still passing (config tests, state tests, agent_graph tests)
- ✅ No regressions introduced
- ✅ All supervisor node tests passing (22 tests)

---

## Key Design Decisions

1. **Lazy Imports**: Used `__getattr__()` pattern in `supervisor/__init__.py` to:
   - Break circular dependencies (`state.py` → `summarize_conversation` → `supervisor/__init__.py` → `call_researcher` → `state.py`)
   - Allow `state.py` to import `manage_chat_history` without triggering import of other nodes
   - Improve testability and reduce import overhead

2. **Helper Functions Location**: Each helper function stays in the same file as the node that uses it:
   - `_make_supervisor_decision()` in `supervisor.py`
   - `_handle_direct_answer()` in `direct_answer.py`
   - `_generate_final_report()` in `final_report.py`
   - This keeps related code together and improves maintainability

3. **State Logger Access**: Nodes access `_state_logger` from `orchestrator` module temporarily:
   - This is a temporary solution until Phase 8 (Logging Migration)
   - Allows nodes to be migrated without refactoring logging infrastructure
   - Tests patch `orchestrator._state_logger` to mock logging

4. **Route Function Location**: Moved `route_supervisor()` to `agent_graph.py`:
   - As per user decision
   - Keeps routing logic close to where it's used (conditional edges)
   - Separates routing from node implementations

5. **Manage Chat History Location**: Kept `manage_chat_history()` in `summarize_conversation.py`:
   - As per user decision
   - Reducer function stays with the node that uses it
   - Imported by `state.py` for type annotation

6. **Backward Compatibility**: Maintained existing import patterns:
   - `main.py` continues to work without changes
   - `from polyplexity_agent import run_research_agent, main_graph, _checkpointer` still works
   - Lazy imports ensure no breaking changes

---

## Migration Impact

### Before Phase 4
- All supervisor nodes in `orchestrator.py` (475 lines)
- `summarize_conversation_node` in `summarizer.py`
- `route_supervisor` in `orchestrator.py`
- Helper functions scattered throughout `orchestrator.py`
- No dedicated test files for supervisor nodes

### After Phase 4
- Supervisor nodes organized in `graphs/nodes/supervisor/`:
  - Each node in its own file with helpers
  - Clear separation of concerns
  - Easy to locate and modify specific nodes
- `orchestrator.py` reduced to 68 lines (86% reduction)
- `route_supervisor` moved to `agent_graph.py`
- Comprehensive test coverage (22 tests for supervisor nodes)
- Lazy imports prevent circular dependencies

---

## Verification Checklist

- ✅ All supervisor nodes extracted to `graphs/nodes/supervisor/`
- ✅ Helper functions moved to respective node files
- ✅ `route_supervisor` moved to `agent_graph.py`
- ✅ `manage_chat_history` moved to `summarize_conversation.py`
- ✅ All imports updated across codebase
- ✅ Lazy imports implemented to avoid circular dependencies
- ✅ Tests created and passing (22 supervisor node tests)
- ✅ No linter errors
- ✅ All existing tests still passing (43 total tests)
- ✅ `orchestrator.py` cleaned up (86% reduction)
- ✅ Backward compatibility maintained
- ✅ Virtual environment used for testing (`backend/.venv/`)

---

## Next Steps

Phase 4 is complete. Ready to proceed to **Phase 5: Researcher Subgraph Migration**.

Phase 5 will involve:
- Moving researcher nodes from `researcher.py` → `graphs/nodes/researcher/`
- Moving graph building logic to `graphs/subgraphs/researcher.py`
- Creating test files for researcher nodes
- Updating imports in supervisor nodes that call researcher subgraph

---

## Notes

- **Package Structure**: All changes are within the `polyplexity_agent` installable package
- **Package Installation**: Package must be installed in editable mode (`pip install -e .`) for imports to work
- **Import Pattern**: All imports use package imports: `from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node`
- **Test Imports**: Tests import from installed package (or local source as fallback)
- **Lazy Imports**: The lazy import pattern in `supervisor/__init__.py` resolved circular dependency issues
- **Circular Dependencies**: Resolved by importing `manage_chat_history` eagerly and other nodes lazily
- **State Logger**: Nodes temporarily access `_state_logger` from `orchestrator` (will be refactored in Phase 8)
- **File Size Reduction**: `orchestrator.py` reduced from 475 lines to 68 lines (86% reduction)
- **Test Coverage**: 22 comprehensive tests for supervisor nodes with mocking and fixtures
- **All existing functionality preserved** - this was a non-breaking refactor
- **Tests can now run independently** without requiring full application dependencies
