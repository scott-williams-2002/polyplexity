# Testing Guide

This directory contains comprehensive tests for the polyplexity_agent package. The test suite includes unit tests, integration tests, end-to-end tests, and performance benchmarks.

## Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── fixtures/                # Test fixtures and sample data
│   ├── sample_states.py     # State factory functions
│   ├── mock_responses.py    # Mock response factories
│   └── sample_events.json   # Sample SSE events
├── graphs/                  # Graph tests
│   ├── test_agent_graph.py  # Main graph tests
│   ├── test_end_to_end.py  # End-to-end tests
│   └── test_state.py        # State tests
├── integration/             # Integration tests
│   ├── test_researcher_subgraph_integration.py
│   ├── test_market_research_subgraph_integration.py
│   ├── test_agent_graph_integration.py
│   ├── test_streaming_integration.py
│   └── test_state_management_integration.py
├── performance/             # Performance tests
│   ├── test_graph_execution_performance.py
│   └── test_streaming_performance.py
└── [other test directories]
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test types
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# End-to-end tests only
pytest -m e2e

# Performance tests (slow)
pytest -m slow
```

### Run with coverage
```bash
pytest --cov=polyplexity_agent --cov-report=html
```

### Run specific test file
```bash
pytest tests/graphs/test_end_to_end.py
```

## Using Shared Fixtures

All shared fixtures are defined in `conftest.py` and are automatically available to all tests. Import them in your test functions:

```python
def test_example(mock_settings, mock_llm, sample_supervisor_state):
    """Test using shared fixtures."""
    # Use fixtures directly
    assert mock_settings is not None
    assert sample_supervisor_state["user_request"] == "What is the weather?"
```

### Available Fixtures

- `mock_settings`: Settings instance with temp directory
- `mock_llm`: Mock LLM instance
- `mock_supervisor_decision_research`: Mock decision for research path
- `mock_supervisor_decision_finish`: Mock decision for finish path
- `mock_supervisor_decision_clarify`: Mock decision for clarification path
- `sample_supervisor_state`: Complete SupervisorState sample
- `sample_researcher_state`: Complete ResearcherState sample
- `sample_market_research_state`: Complete MarketResearchState sample
- `mock_checkpointer`: Mock checkpointer instance
- `mock_state_logger`: Mock StateLogger instance
- `mock_researcher_graph`: Mock researcher subgraph
- `mock_market_research_graph`: Mock market research subgraph
- `mock_graph`: Mock main agent graph
- `mock_tavily_search`: Mock TavilySearch tool
- `mock_polymarket_search`: Mock Polymarket search function
- `mock_database`: Mock database connection
- `mock_search_queries`: Mock SearchQueries response
- `mock_tavily_results`: Mock Tavily search results
- `mock_polymarket_results`: Mock Polymarket results
- `mock_queries_response`: Mock market queries response
- `mock_ranking_response`: Mock market ranking response
- `mock_evaluation_response`: Mock market evaluation response

## Mocking Patterns

### Mocking LLM Calls

```python
from unittest.mock import Mock, patch

@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_with_llm_mock(mock_create_llm):
    """Test with mocked LLM."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Mock response"
    mock_create_llm.return_value = mock_llm
    
    # Your test code here
```

### Mocking Node Functions

```python
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.supervisor_node")
def test_with_node_mock(mock_node):
    """Test with mocked node."""
    mock_node.return_value = {"next_topic": "FINISH"}
    
    # Your test code here
```

### Mocking External APIs

```python
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
def test_with_api_mock(mock_tavily):
    """Test with mocked API."""
    mock_tool = Mock()
    mock_tool.invoke.return_value = {"results": []}
    mock_tavily.return_value = mock_tool
    
    # Your test code here
```

## Testing Node Functions

Node functions take state dictionaries and return state updates:

```python
def test_node_function(sample_supervisor_state):
    """Test a node function."""
    from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node
    
    with patch("polyplexity_agent.utils.helpers.create_llm_model") as mock_llm:
        # Setup mocks
        result = supervisor_node(sample_supervisor_state)
        
        # Assertions
        assert "next_topic" in result
```

## Testing State Transitions

Test how state changes through graph execution:

```python
def test_state_transition(sample_supervisor_state):
    """Test state transition."""
    initial_state = sample_supervisor_state.copy()
    
    # Execute node
    updated_state = some_node(initial_state)
    
    # Verify state changes
    assert updated_state["iterations"] == initial_state["iterations"] + 1
```

## Testing Streaming Events

Test that events are properly streamed:

```python
def test_streaming(mock_graph):
    """Test event streaming."""
    def mock_stream(initial_state, config, stream_mode):
        yield ("custom", {"event": "test_event"})
        yield ("updates", {"node": {"field": "value"}})
    
    mock_graph.stream = mock_stream
    
    events = list(run_research_agent("test", graph=mock_graph))
    
    assert len(events) > 0
    assert any("test_event" in str(e) for e in events)
```

## Testing Subgraphs

Test subgraph execution end-to-end:

```python
@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
def test_subgraph(sample_researcher_state, mock_llm):
    """Test subgraph execution."""
    from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
    
    # Setup mocks
    result = researcher_graph.invoke(sample_researcher_state)
    
    # Verify results
    assert "research_summary" in result
```

## Testing Error Scenarios

Test error handling:

```python
def test_error_handling(mock_graph):
    """Test error handling."""
    def mock_stream(initial_state, config, stream_mode):
        raise Exception("Test error")
    
    mock_graph.stream = mock_stream
    
    with pytest.raises(Exception):
        list(run_research_agent("test", graph=mock_graph))
```

## Test Markers

Tests are marked with pytest markers for organization:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.slow`: Slow-running tests (performance)
- `@pytest.mark.performance`: Performance benchmarks

## Coverage Configuration

Coverage is configured in `.coveragerc` at the backend root. To generate coverage reports:

```bash
pytest --cov=polyplexity_agent --cov-report=html
```

Coverage reports exclude:
- Test files (`*/tests/*`)
- Migration files (`*/migrations/*`)
- Cache files (`*/__pycache__/*`)

## Best Practices

1. **Use shared fixtures**: Import fixtures from `conftest.py` instead of creating local ones
2. **Mock external dependencies**: Always mock LLM calls, API calls, and database access
3. **Test edge cases**: Include tests for empty states, max iterations, error conditions
4. **Keep tests focused**: Each test should verify one specific behavior
5. **Use descriptive names**: Test function names should clearly describe what they test
6. **Follow CODING_STYLE.md**: Use double quotes, type hints, Google docstrings
7. **Test event emission**: Verify that nodes emit expected events
8. **Test state accumulation**: Ensure accumulating fields work correctly
9. **Test error handling**: Verify errors are handled gracefully and events are emitted

## Common Testing Patterns

### Testing with Structured Output

When testing nodes that use structured output (Pydantic models):

```python
@pytest.mark.unit
@patch("polyplexity_agent.utils.helpers.create_llm_model")
def test_node_with_structured_output(mock_create_llm, sample_state):
    """Test node that uses structured output."""
    # Create mock structured response
    mock_llm = Mock()
    structured_response = Mock(spec=SupervisorDecision)
    structured_response.next_step = "research"
    structured_response.research_topic = "topic"
    structured_response.reasoning = "reasoning"
    
    # Configure mock chain
    mock_llm.with_structured_output.return_value.with_retry.return_value.invoke.return_value = structured_response
    mock_create_llm.return_value = mock_llm
    
    # Execute
    result = node_name(sample_state)
    
    # Assertions
    assert result["next_topic"] == "topic"
```

### Testing Event Emission

Verify that nodes emit expected events:

```python
@pytest.mark.unit
@patch("langgraph.config.get_stream_writer")
def test_node_emits_events(mock_get_writer, sample_state):
    """Test that node emits expected events."""
    mock_writer = Mock()
    mock_get_writer.return_value = mock_writer
    
    # Execute node
    result = node_name(sample_state)
    
    # Verify events were written
    assert mock_writer.called
    
    # Check specific event
    call_args_list = mock_writer.call_args_list
    events = [call[0][0] for call in call_args_list]
    
    assert any(event.get("event") == "expected_event" for event in events)
```

### Testing State Accumulation

Test that accumulating fields work correctly:

```python
@pytest.mark.unit
def test_state_accumulation(sample_state):
    """Test that accumulating fields accumulate correctly."""
    state1 = sample_state.copy()
    state1["research_notes"] = ["Note 1"]
    
    # First node execution
    result1 = node_name(state1)
    assert len(result1.get("research_notes", [])) == 1
    
    # Second node execution (simulating accumulation)
    state2 = {**state1, **result1}
    state2["research_notes"] = state1["research_notes"] + result1.get("research_notes", [])
    result2 = another_node(state2)
    
    # Verify accumulation
    assert len(state2["research_notes"]) >= 1
```

### Testing Subgraph Integration

Test how subgraphs integrate with main graph:

```python
@pytest.mark.integration
@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("langgraph.config.get_stream_writer")
def test_subgraph_integration(mock_get_writer, mock_logger, sample_state):
    """Test subgraph integration with main graph."""
    mock_writer = Mock()
    mock_get_writer.return_value = mock_writer
    
    # Mock subgraph nodes
    with patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model") as mock_llm:
        # Setup mocks...
        
        # Execute subgraph
        from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
        result = researcher_graph.invoke(sample_state)
        
        # Verify subgraph events were forwarded
        assert mock_writer.called
        
        # Verify result
        assert "research_summary" in result
```

### Testing Error Scenarios

Test various error conditions:

```python
@pytest.mark.unit
def test_node_handles_api_error(sample_state):
    """Test node handles API errors gracefully."""
    with patch("polyplexity_agent.tools.polymarket.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("API error")
        
        with pytest.raises(Exception):
            node_name(sample_state)
        
        # Verify error event was emitted (check via stream_writer mock)
```

### Testing Empty States

Test nodes handle empty/minimal states:

```python
@pytest.mark.unit
def test_node_with_empty_state():
    """Test node handles empty state."""
    empty_state = {
        "user_request": "",
        "research_notes": [],
        "iterations": 0,
    }
    
    result = node_name(empty_state)
    
    # Verify node doesn't crash and returns valid result
    assert isinstance(result, dict)
    assert "execution_trace" in result
```

### Testing Max Iterations

Test nodes respect iteration limits:

```python
@pytest.mark.unit
def test_node_max_iterations(sample_state):
    """Test node handles max iterations."""
    state = sample_state.copy()
    state["iterations"] = 10  # Max iterations
    
    result = supervisor_node(state)
    
    # Verify node forces finish
    assert result["next_topic"] == "FINISH"
```

## Edge Cases to Test

1. **Empty states**: Nodes should handle empty/minimal states gracefully
2. **Max iterations**: Nodes should respect iteration limits
3. **Missing fields**: Nodes should handle missing optional fields
4. **API failures**: Nodes should handle external API failures
5. **LLM failures**: Nodes should handle LLM call failures
6. **Database failures**: Nodes should handle database errors
7. **Invalid state**: Nodes should handle invalid state gracefully
8. **Concurrent execution**: Test thread safety if applicable

## Troubleshooting

### Tests fail with import errors

**Problem**: `ModuleNotFoundError: No module named 'polyplexity_agent'`

**Solution**: Ensure the package is installed in editable mode:
```bash
cd polyplexity/backend/polyplexity_agent
pip install -e .
```

**Verification**: 
```bash
python -c "from polyplexity_agent import run_research_agent; print('Package installed correctly')"
```

### Fixtures not found

**Problem**: `FixtureNotFoundError: fixture 'mock_llm' not found`

**Solution**: 
1. Ensure `conftest.py` is in the `tests/` directory
2. Verify pytest can find it: `pytest --collect-only`
3. Check that fixture is defined in `conftest.py`

### Mock not working

**Problem**: Mock not being applied, real function being called

**Solution**: Check that you're patching the correct import path. Use the full module path where the function is **used**, not where it's defined:

```python
# Correct: Patch where it's used
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.create_llm_model")

# Incorrect: Patch where it's defined
@patch("polyplexity_agent.utils.helpers.create_llm_model")
```

**Debugging**: Add print statements or use `mock_create_llm.assert_called()` to verify mock is being used.

### State logger errors

**Problem**: `AttributeError: 'NoneType' object has no attribute 'write'`

**Solution**: Mock state logger in tests:
```python
@patch("polyplexity_agent.utils.state_manager._state_logger", None)
def test_node():
    """Test with no state logger."""
    pass
```

Or use the fixture:
```python
def test_node(mock_state_logger):
    """Test with mocked state logger."""
    pass
```

### Async test issues

**Problem**: Async tests not running or hanging

**Solution**: 
1. Install `pytest-asyncio`: `pip install pytest-asyncio`
2. Use `@pytest.mark.asyncio` decorator:
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Coverage not including files

**Problem**: Coverage report missing files

**Solution**: 
1. Check `.coveragerc` or coverage configuration
2. Verify files are not excluded
3. Use `--cov=polyplexity_agent` to specify package name
4. Check that files are imported during test execution

### Tests hanging or timing out

**Problem**: Tests hang indefinitely

**Solution**:
1. Check for unmocked external calls (LLM, APIs, database)
2. Verify mocks are set up correctly
3. Use `pytest --timeout=10` to set timeout
4. Check for infinite loops in code

### State not updating correctly

**Problem**: State updates not working as expected

**Solution**:
1. Verify state TypedDict definition includes the field
2. Check that field uses correct reducer (if accumulating)
3. Verify node returns state updates correctly
4. Check that state updates are merged correctly by LangGraph

## Additional Resources

- **Comprehensive Testing Guide**: See `polyplexity_agent/docs/TESTING.md` for detailed testing patterns and examples
- **Development Guide**: See `polyplexity_agent/docs/DEVELOPMENT.md` for templates and patterns
- **Coding Style**: See `docs/CODING_STYLE.md` for code style guidelines
