# Testing Guide

This guide provides comprehensive information about testing the `polyplexity_agent` library, including testing philosophy, test structure, writing tests, mocking patterns, and best practices.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Writing Tests](#writing-tests)
5. [Mocking Patterns](#mocking-patterns)
6. [Fixtures](#fixtures)
7. [Test Markers](#test-markers)
8. [Coverage](#coverage)
9. [Best Practices](#best-practices)

## Testing Philosophy

### Test Types

1. **Unit Tests**: Test individual functions/nodes in isolation
   - Mock all external dependencies (LLM, APIs, database)
   - Fast execution
   - Focus on logic correctness

2. **Integration Tests**: Test component interactions
   - Test subgraph execution end-to-end
   - Mock external services but test internal integration
   - Verify state transitions

3. **End-to-End Tests**: Test complete workflows
   - Test full graph execution
   - Mock external services
   - Verify complete request → response flow

4. **Performance Tests**: Benchmark execution time
   - Marked with `@pytest.mark.slow`
   - Measure graph execution time
   - Identify performance bottlenecks

### Testing Strategy

- **Mock external dependencies**: LLM calls, API calls, database access
- **Use fixtures**: Reusable test data and mocks
- **Test edge cases**: Empty states, max iterations, error conditions
- **Verify state transitions**: Ensure state updates correctly
- **Test event emission**: Verify events are emitted correctly
- **Coverage goal**: Aim for >80% code coverage

## Test Structure

### Directory Organization

```
tests/
├── conftest.py              # Shared fixtures
├── fixtures/                # Test data files
│   ├── sample_states.py     # State factory functions
│   ├── mock_responses.py    # Mock response factories
│   └── sample_events.json   # Sample SSE events
├── graphs/                  # Graph tests
│   ├── test_agent_graph.py  # Main graph tests
│   ├── test_state.py        # State tests
│   ├── test_end_to_end.py   # End-to-end tests
│   └── nodes/               # Node tests
│       ├── supervisor/
│       ├── researcher/
│       └── market_research/
├── integration/             # Integration tests
│   ├── test_researcher_subgraph_integration.py
│   ├── test_market_research_subgraph_integration.py
│   ├── test_agent_graph_integration.py
│   ├── test_streaming_integration.py
│   └── test_state_management_integration.py
├── streaming/               # Streaming tests
│   ├── test_sse.py
│   ├── test_event_processor.py
│   └── test_event_serializers.py
├── subgraphs/               # Subgraph tests
│   ├── test_researcher.py
│   └── test_market_research.py
└── [other test directories]
```

### Test File Naming

- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/graphs/test_agent_graph.py

# Run specific test function
pytest tests/graphs/test_agent_graph.py::test_create_agent_graph

# Run with verbose output
pytest -v

# Run with output capture disabled (see print statements)
pytest -s
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only end-to-end tests
pytest -m e2e

# Run performance tests (slow)
pytest -m slow

# Skip slow tests
pytest -m "not slow"
```

### Coverage

```bash
# Run with coverage
pytest --cov=polyplexity_agent --cov-report=html

# View coverage report
open htmlcov/index.html

# Coverage with terminal output
pytest --cov=polyplexity_agent --cov-report=term-missing
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto
```

## Writing Tests

### Basic Test Structure

```python
"""
Tests for [module/component name].
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node
from polyplexity_agent.graphs.state import SupervisorState


@pytest.mark.unit
def test_supervisor_node_research_path(sample_supervisor_state, mock_llm):
    """Test supervisor node chooses research path."""
    # Setup
    state = sample_supervisor_state.copy()
    
    # Execute
    result = supervisor_node(state)
    
    # Assert
    assert "next_topic" in result
    assert result["next_topic"] != "FINISH"
    assert "iterations" in result
```

### Node Tests

**Template**:

```python
@pytest.mark.unit
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_node_name(mock_create_llm, sample_state):
    """Test [node name] node."""
    # Setup mocks
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Mock response"
    mock_create_llm.return_value = mock_llm
    
    # Execute
    result = node_name(sample_state)
    
    # Assertions
    assert "expected_field" in result
    assert result["expected_field"] == "expected_value"
```

**Example**:

```python
@pytest.mark.unit
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_supervisor_node(mock_create_llm, sample_supervisor_state):
    """Test supervisor node."""
    # Setup mock LLM
    mock_llm = Mock()
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "research"
    decision.research_topic = "test topic"
    decision.reasoning = "Need research"
    decision.answer_format = "concise"
    
    mock_llm.with_structured_output.return_value.with_retry.return_value.invoke.return_value = decision
    mock_create_llm.return_value = mock_llm
    
    # Execute
    result = supervisor_node(sample_supervisor_state)
    
    # Assertions
    assert "next_topic" in result
    assert result["next_topic"] == "test topic"
    assert "iterations" in result
    assert "execution_trace" in result
```

### Subgraph Tests

**Template**:

```python
@pytest.mark.integration
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
def test_researcher_subgraph(mock_llm, sample_researcher_state):
    """Test researcher subgraph execution."""
    # Setup mocks
    # ... mock LLM responses
    
    # Execute subgraph
    from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
    result = researcher_graph.invoke(sample_researcher_state)
    
    # Assertions
    assert "research_summary" in result
    assert len(result["research_summary"]) > 0
```

**Example**:

```python
@pytest.mark.integration
@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
def test_researcher_subgraph(mock_llm, mock_logger, sample_researcher_state):
    """Test researcher subgraph end-to-end."""
    # Setup mock LLM
    mock_llm_instance = Mock()
    queries_response = Mock(spec=SearchQueries)
    queries_response.queries = ["query1", "query2"]
    
    mock_llm_instance.with_structured_output.return_value.with_retry.return_value.invoke.return_value = queries_response
    mock_llm_instance.invoke.return_value.content = "Research summary"
    mock_llm.return_value = mock_llm_instance
    
    # Mock Tavily search
    with patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch") as mock_tavily:
        mock_tool = Mock()
        mock_tool.invoke.return_value = {"results": [{"content": "Result 1"}]}
        mock_tavily.return_value = mock_tool
        
        # Execute
        from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
        result = researcher_graph.invoke(sample_researcher_state)
        
        # Assertions
        assert "research_summary" in result
        assert len(result["research_summary"]) > 0
```

### Graph Tests

**Template**:

```python
@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
def test_agent_graph_execution(mock_graph, sample_supervisor_state):
    """Test complete agent graph execution."""
    # Setup mock graph stream
    def mock_stream(initial_state, config, stream_mode):
        yield ("custom", {"event": "supervisor_decision"})
        yield ("updates", {"supervisor": {"next_topic": "test"}})
    
    mock_graph.stream = mock_stream
    
    # Execute
    from polyplexity_agent.entrypoint import run_research_agent
    events = list(run_research_agent("test query", graph=mock_graph))
    
    # Assertions
    assert len(events) > 0
```

### Streaming Tests

**Template**:

```python
@pytest.mark.unit
def test_sse_generator():
    """Test SSE generator formats events correctly."""
    # Create mock event iterator
    def mock_iterator():
        yield ("custom", {"event": "test_event", "data": "value"})
        yield ("updates", {"node": {"field": "value"}})
    
    # Execute
    from polyplexity_agent.streaming import create_sse_generator
    import asyncio
    
    async def run_test():
        sse_lines = []
        async for line in create_sse_generator(mock_iterator()):
            sse_lines.append(line)
        return sse_lines
    
    result = asyncio.run(run_test())
    
    # Assertions
    assert len(result) > 0
    assert all(line.startswith("data: ") for line in result)
```

### State Transition Tests

**Template**:

```python
@pytest.mark.unit
def test_state_transition(sample_state):
    """Test state transition through node."""
    # Initial state
    initial_state = sample_state.copy()
    initial_iterations = initial_state.get("iterations", 0)
    
    # Execute node
    result = node_name(initial_state)
    
    # Verify state updates
    assert result["iterations"] == initial_iterations + 1
    assert "new_field" in result
```

## Mocking Patterns

### Mocking LLM Calls

**Pattern 1: Mock create_llm_model**:

```python
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_with_llm_mock(mock_create_llm):
    """Test with mocked LLM."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Mock response"
    mock_create_llm.return_value = mock_llm
    
    # Test code
```

**Pattern 2: Mock structured output**:

```python
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_with_structured_output(mock_create_llm):
    """Test with structured output."""
    mock_llm = Mock()
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "research"
    decision.research_topic = "topic"
    
    mock_llm.with_structured_output.return_value.with_retry.return_value.invoke.return_value = decision
    mock_create_llm.return_value = mock_llm
    
    # Test code
```

**Pattern 3: Use fixture**:

```python
def test_with_llm_fixture(mock_llm):
    """Test using mock_llm fixture."""
    # mock_llm is already configured
    # Test code
```

### Mocking External APIs

**Pattern**:

```python
@patch("polyplexity_agent.tools.polymarket.requests.get")
def test_with_api_mock(mock_get):
    """Test with mocked API."""
    mock_response = Mock()
    mock_response.json.return_value = {"events": []}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    # Test code
    from polyplexity_agent.tools.polymarket import search_markets
    result = search_markets("query")
    
    assert isinstance(result, list)
```

### Mocking Database

**Pattern**:

```python
@patch("polyplexity_agent.db_utils.database_manager.get_database_manager")
def test_with_database_mock(mock_get_db):
    """Test with mocked database."""
    mock_db = Mock()
    mock_db.get_thread.return_value = None
    mock_db.save_thread_name = Mock()
    mock_get_db.return_value = mock_db
    
    # Test code
```

### Mocking Graph Stream

**Pattern**:

```python
def test_with_graph_stream_mock(mock_graph):
    """Test with mocked graph stream."""
    def mock_stream(initial_state, config, stream_mode):
        yield ("custom", {"event": "test"})
        yield ("updates", {"node": {"field": "value"}})
    
    mock_graph.stream = mock_stream
    
    # Test code
```

### Mocking Stream Writer

**Pattern**:

```python
@patch("langgraph.config.get_stream_writer")
def test_with_stream_writer_mock(mock_get_writer):
    """Test with mocked stream writer."""
    mock_writer = Mock()
    mock_get_writer.return_value = mock_writer
    
    # Execute node that emits events
    result = node_name(state)
    
    # Verify events were written
    assert mock_writer.called
```

## Fixtures

### Using Fixtures

Fixtures are automatically available to test functions:

```python
def test_example(mock_settings, mock_llm, sample_supervisor_state):
    """Test using fixtures."""
    # Use fixtures directly
    assert mock_settings is not None
    assert sample_supervisor_state["user_request"] == "What is the weather?"
```

### Available Fixtures

See `tests/conftest.py` for all fixtures. Common ones:

- **`mock_settings`**: Settings instance with temp directory
- **`mock_llm`**: Mock LLM instance
- **`sample_supervisor_state`**: Complete SupervisorState sample
- **`sample_researcher_state`**: Complete ResearcherState sample
- **`mock_checkpointer`**: Mock checkpointer instance
- **`mock_state_logger`**: Mock StateLogger instance
- **`mock_graph`**: Mock main agent graph
- **`mock_researcher_graph`**: Mock researcher subgraph

### Creating Custom Fixtures

Add to `tests/conftest.py`:

```python
@pytest.fixture
def custom_fixture():
    """Custom fixture description."""
    # Setup
    value = "test_value"
    yield value
    # Teardown (if needed)
```

## Test Markers

### Available Markers

- **`@pytest.mark.unit`**: Unit tests
- **`@pytest.mark.integration`**: Integration tests
- **`@pytest.mark.e2e`**: End-to-end tests
- **`@pytest.mark.slow`**: Slow-running tests (performance)

### Using Markers

```python
@pytest.mark.unit
def test_unit_test():
    """Unit test."""
    pass

@pytest.mark.integration
def test_integration_test():
    """Integration test."""
    pass

@pytest.mark.e2e
def test_e2e_test():
    """End-to-end test."""
    pass

@pytest.mark.slow
def test_performance():
    """Performance test."""
    pass
```

## Coverage

### Coverage Configuration

Coverage is configured in `pyproject.toml` or `.coveragerc`. Exclusions:

- Test files (`*/tests/*`)
- Migration files (`*/migration/*`)
- Cache files (`*/__pycache__/*`)

### Coverage Goals

- **Overall**: >80% code coverage
- **Critical paths**: >90% coverage (nodes, entrypoint, streaming)
- **Utilities**: >70% coverage acceptable

### Viewing Coverage

```bash
# Generate HTML report
pytest --cov=polyplexity_agent --cov-report=html

# View in browser
open htmlcov/index.html

# Terminal report with missing lines
pytest --cov=polyplexity_agent --cov-report=term-missing
```

## Best Practices

### 1. Use Descriptive Test Names

```python
# Good
def test_supervisor_node_chooses_research_path_when_insufficient_info():
    pass

# Bad
def test_supervisor():
    pass
```

### 2. Test One Thing Per Test

```python
# Good
def test_supervisor_node_sets_next_topic():
    """Test that supervisor node sets next_topic."""
    pass

def test_supervisor_node_increments_iterations():
    """Test that supervisor node increments iterations."""
    pass

# Bad
def test_supervisor_node():
    """Test supervisor node does everything."""
    pass
```

### 3. Use Fixtures for Common Setup

```python
# Good
def test_node(sample_supervisor_state, mock_llm):
    """Test using fixtures."""
    pass

# Bad
def test_node():
    """Test with manual setup."""
    state = {
        "user_request": "test",
        "research_notes": [],
        # ... many fields
    }
    # ... manual mock setup
```

### 4. Mock External Dependencies

```python
# Good
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_node(mock_llm):
    """Test with mocked LLM."""
    pass

# Bad
def test_node():
    """Test with real LLM (slow, unreliable)."""
    pass
```

### 5. Test Edge Cases

```python
def test_node_with_empty_state():
    """Test node handles empty state."""
    state = {}
    result = node_name(state)
    assert result is not None

def test_node_with_max_iterations():
    """Test node handles max iterations."""
    state = {"iterations": 10}
    result = node_name(state)
    assert result["next_topic"] == "FINISH"
```

### 6. Verify Event Emission

```python
@patch("langgraph.config.get_stream_writer")
def test_node_emits_events(mock_get_writer):
    """Test node emits events."""
    mock_writer = Mock()
    mock_get_writer.return_value = mock_writer
    
    result = node_name(state)
    
    # Verify events were emitted
    assert mock_writer.called
    call_args = mock_writer.call_args[0][0]
    assert call_args["event"] == "expected_event"
```

### 7. Test Error Handling

```python
def test_node_handles_errors():
    """Test node handles errors gracefully."""
    with patch("polyplexity_agent.utils.helpers.create_llm_model") as mock_llm:
        mock_llm.side_effect = Exception("API error")
        
        with pytest.raises(Exception):
            node_name(state)
        
        # Verify error event was emitted
        # (check via stream_writer mock)
```

### 8. Use Type Hints

```python
def test_node(sample_supervisor_state: SupervisorState) -> None:
    """Test with type hints."""
    result = node_name(sample_supervisor_state)
    assert isinstance(result, dict)
```

### 9. Document Test Purpose

```python
def test_node():
    """
    Test that node correctly processes state and returns updates.
    
    Verifies:
    - State field updates
    - Event emission
    - Error handling
    """
    pass
```

### 10. Keep Tests Fast

```python
# Good: Mock external calls
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_fast(mock_llm):
    """Fast test with mocks."""
    pass

# Bad: Real API calls
def test_slow():
    """Slow test with real API."""
    result = real_api_call()  # Don't do this
```

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'polyplexity_agent'`

**Solution**: Install package in editable mode:
```bash
cd polyplexity/backend/polyplexity_agent
pip install -e .
```

### Fixtures Not Found

**Problem**: `FixtureNotFoundError: fixture 'mock_llm' not found`

**Solution**: Ensure `conftest.py` is in `tests/` directory and pytest can find it.

### Mock Not Working

**Problem**: Mock not being applied

**Solution**: Check patch path - use full module path where function is used:
```python
# Correct: Patch where it's used
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.create_llm_model")

# Incorrect: Patch where it's defined
@patch("polyplexity_agent.utils.helpers.create_llm_model")
```

### State Logger Errors

**Problem**: `AttributeError: 'NoneType' object has no attribute 'write'`

**Solution**: Mock state logger in tests:
```python
@patch("polyplexity_agent.utils.state_manager._state_logger", None)
def test_node():
    """Test with no state logger."""
    pass
```

### Async Test Issues

**Problem**: Async tests not running

**Solution**: Use `pytest-asyncio`:
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

## Example: Complete Test File

```python
"""
Tests for supervisor node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.models import SupervisorDecision


@pytest.mark.unit
@patch("polyplexity_agent.utils.state_manager._state_logger", None)
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_supervisor_node_research_path(mock_create_llm, sample_supervisor_state):
    """Test supervisor node chooses research path."""
    # Setup mock LLM
    mock_llm = Mock()
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "research"
    decision.research_topic = "test topic"
    decision.reasoning = "Need research"
    decision.answer_format = "concise"
    
    mock_llm.with_structured_output.return_value.with_retry.return_value.invoke.return_value = decision
    mock_create_llm.return_value = mock_llm
    
    # Execute
    result = supervisor_node(sample_supervisor_state)
    
    # Assertions
    assert "next_topic" in result
    assert result["next_topic"] == "test topic"
    assert "iterations" in result
    assert result["iterations"] == sample_supervisor_state.get("iterations", 0) + 1
    assert "execution_trace" in result


@pytest.mark.unit
@patch("polyplexity_agent.utils.state_manager._state_logger", None)
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_supervisor_node_finish_path(mock_create_llm, sample_supervisor_state):
    """Test supervisor node chooses finish path."""
    # Setup mock LLM
    mock_llm = Mock()
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "finish"
    decision.research_topic = ""
    decision.reasoning = "Have enough info"
    decision.answer_format = "concise"
    
    mock_llm.with_structured_output.return_value.with_retry.return_value.invoke.return_value = decision
    mock_create_llm.return_value = mock_llm
    
    # Execute
    result = supervisor_node(sample_supervisor_state)
    
    # Assertions
    assert result["next_topic"] == "FINISH"
    assert "iterations" in result


@pytest.mark.unit
@patch("polyplexity_agent.utils.state_manager._state_logger", None)
def test_supervisor_node_max_iterations(sample_supervisor_state):
    """Test supervisor node forces finish at max iterations."""
    state = sample_supervisor_state.copy()
    state["iterations"] = 10
    
    # Execute
    result = supervisor_node(state)
    
    # Assertions
    assert result["next_topic"] == "FINISH"
```
