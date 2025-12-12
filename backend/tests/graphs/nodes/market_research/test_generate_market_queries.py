"""
Tests for generate_market_queries node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.market_research.generate_market_queries import generate_market_queries_node
from polyplexity_agent.graphs.state import MarketResearchState


@pytest.fixture
def sample_state():
    """Create a sample market research state."""
    return {
        "original_topic": "2024 US presidential election",
        "market_queries": [],
        "raw_events": [],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }


@pytest.fixture
def mock_queries_response():
    """Create a mock queries response."""
    return {"queries": ["2024 election", "presidential race", "election predictions"]}


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.log_node_state")
def test_generate_market_queries_node(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
    mock_queries_response,
):
    """Test generate_market_queries_node generates queries successfully."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.invoke.return_value = mock_queries_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    result = generate_market_queries_node(sample_state)
    
    assert "market_queries" in result
    assert len(result["market_queries"]) == 3
    assert result["market_queries"] == ["2024 election", "presidential race", "election predictions"]
    assert "reasoning_trace" in result
    assert "execution_trace" in result
    assert len(result["execution_trace"]) == 2
    
    # Verify writer was called for events
    assert mock_writer.call_count >= 3  # trace events, generated_market_queries
    
    # Verify log_node_state was called
    assert mock_log_node_state.call_count == 2  # BEFORE and AFTER


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.log_node_state")
def test_generate_market_queries_node_different_topics(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    mock_queries_response,
):
    """Test generate_market_queries_node with different topics."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.invoke.return_value = mock_queries_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    # Use return_value instead of side_effect to avoid exhaustion
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    topics = ["crypto prices", "sports betting", "climate change"]
    for topic in topics:
        state = {
            "original_topic": topic,
            "market_queries": [],
            "raw_events": [],
            "candidate_markets": [],
            "approved_markets": [],
            "reasoning_trace": [],
        }
        result = generate_market_queries_node(state)
        assert "market_queries" in result
        assert len(result["market_queries"]) > 0


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.log_node_state")
def test_generate_market_queries_node_error_handling(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test generate_market_queries_node error handling."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM to raise an exception
    mock_create_llm_model.side_effect = Exception("LLM error")
    
    with pytest.raises(Exception) as exc_info:
        generate_market_queries_node(sample_state)
    
    assert "LLM error" in str(exc_info.value)
    # Verify error event was written
    assert mock_writer.call_count >= 1
