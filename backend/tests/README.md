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

## Troubleshooting

### Tests fail with import errors
Ensure the package is installed in editable mode:
```bash
cd polyplexity/backend/polyplexity_agent
pip install -e .
```

### Fixtures not found
Ensure `conftest.py` is in the `tests/` directory and pytest can find it.

### Mock not working
Check that you're patching the correct import path. Use the full module path where the function is used, not where it's defined.
