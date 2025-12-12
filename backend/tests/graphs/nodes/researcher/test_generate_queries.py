"""
Tests for generate_queries node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.researcher.generate_queries import generate_queries_node
from polyplexity_agent.graphs.state import ResearcherState
from polyplexity_agent.models import SearchQueries


@pytest.fixture
def sample_state():
    """Create a sample researcher state."""
    return {
        "topic": "artificial intelligence",
        "queries": [],
        "search_results": [],
        "research_summary": "",
        "query_breadth": 3,
    }


@pytest.fixture
def mock_search_queries():
    """Create a mock SearchQueries response."""
    queries = SearchQueries(queries=["AI definition", "AI applications", "AI history"])
    return queries


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.log_node_state")
def test_generate_queries_node(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
    mock_search_queries,
):
    """Test generate_queries_node generates queries successfully."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_search_queries
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    result = generate_queries_node(sample_state)
    
    assert "queries" in result
    assert len(result["queries"]) == 3
    assert result["queries"] == ["AI definition", "AI applications", "AI history"]
    assert "execution_trace" in result
    assert len(result["execution_trace"]) == 2
    
    # Verify writer was called for events
    assert mock_writer.call_count >= 3  # researcher_thinking, trace events, generated_queries
    
    # Verify log_node_state was called
    assert mock_log_node_state.call_count == 2  # BEFORE and AFTER


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.log_node_state")
def test_generate_queries_node_different_topics(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    mock_search_queries,
):
    """Test generate_queries_node with different topics."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_search_queries
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    state = {
        "topic": "quantum computing",
        "queries": [],
        "search_results": [],
        "research_summary": "",
        "query_breadth": 5,
    }
    
    result = generate_queries_node(state)
    
    assert "queries" in result
    assert len(result["queries"]) == 3
    
    # Verify topic was passed to LLM
    invoke_call = mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke
    assert invoke_call.called
    call_args = invoke_call.call_args[0][0]
    assert any("quantum computing" in str(msg.content) for msg in call_args)


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.log_node_state")
def test_generate_queries_node_error_handling(
    mock_log_node_state,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test generate_queries_node handles errors gracefully."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM to raise an error
    mock_create_llm_model.side_effect = Exception("LLM API error")
    
    with pytest.raises(Exception, match="LLM API error"):
        generate_queries_node(sample_state)
    
    # Verify error event was written
    error_calls = [call for call in mock_writer.call_args_list if "error" in str(call)]
    assert len(error_calls) > 0
