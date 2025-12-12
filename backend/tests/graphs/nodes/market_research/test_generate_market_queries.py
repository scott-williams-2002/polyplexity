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
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.log_node_state")
def test_generate_market_queries_node(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
    mock_queries_response,
):
    """Test generate_market_queries_node generates queries successfully."""
    
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
    
    # Verify streaming functions were called
    assert mock_stream_trace_event.call_count >= 2  # node_call and custom trace events
    assert mock_stream_custom_event.call_count >= 1  # generated_market_queries event
    
    # Verify log_node_state was called
    assert mock_log_node_state.call_count == 2  # BEFORE and AFTER


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.log_node_state")
def test_generate_market_queries_node_different_topics(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    mock_queries_response,
):
    """Test generate_market_queries_node with different topics."""
    
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
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.log_node_state")
def test_generate_market_queries_node_error_handling(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test generate_market_queries_node error handling."""
    # Mock LLM to raise an exception
    mock_create_llm_model.side_effect = Exception("LLM error")
    
    with pytest.raises(Exception) as exc_info:
        generate_market_queries_node(sample_state)
    
    assert "LLM error" in str(exc_info.value)
    # Verify error event was streamed
    mock_stream_custom_event.assert_called_once()
    call_args = mock_stream_custom_event.call_args
    assert call_args[0][0] == "error"  # event_name
    assert call_args[0][1] == "generate_market_queries"  # node
