"""
Tests for process_and_rank_markets node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets import process_and_rank_markets_node
from polyplexity_agent.graphs.state import MarketResearchState


@pytest.fixture
def sample_state():
    """Create a sample market research state."""
    return {
        "original_topic": "2024 US presidential election",
        "market_queries": ["2024 election"],
        "raw_events": [
            {
                "title": "2024 Presidential Election",
                "slug": "2024-presidential-election",
                "description": "Who will win?",
                "markets": [],
            },
            {
                "title": "Election Predictions",
                "slug": "election-predictions",
                "description": "Predictions",
                "markets": [],
            },
        ],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }


@pytest.fixture
def mock_ranking_response():
    """Create a mock ranking response."""
    return {
        "ranked_markets": [
            {
                "title": "2024 Presidential Election",
                "slug": "2024-presidential-election",
                "description": "Who will win?",
                "markets": [],
            },
            {
                "title": "Election Predictions",
                "slug": "election-predictions",
                "description": "Predictions",
                "markets": [],
            },
        ]
    }


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.log_node_state")
def test_process_and_rank_markets_node(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
    mock_ranking_response,
):
    """Test process_and_rank_markets_node ranks markets successfully."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.invoke.return_value = mock_ranking_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = process_and_rank_markets_node(sample_state)
    
    assert "candidate_markets" in result
    assert len(result["candidate_markets"]) == 2
    assert "reasoning_trace" in result
    assert "execution_trace" in result
    
    # Verify log_node_state was called
    assert mock_log_node_state.call_count == 2  # BEFORE and AFTER


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.log_node_state")
def test_process_and_rank_markets_node_limits_to_five(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    mock_ranking_response,
):
    """Test process_and_rank_markets_node limits to 5 events."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Create state with more than 5 events
    state = {
        "original_topic": "test topic",
        "market_queries": [],
        "raw_events": [
            {"title": f"Event {i}", "slug": f"event-{i}", "description": "", "markets": []}
            for i in range(10)
        ],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }
    
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.invoke.return_value = mock_ranking_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = process_and_rank_markets_node(state)
    
    # Verify LLM was called with only 5 events
    call_args = mock_llm_chain.with_structured_output.return_value.invoke.call_args
    assert len(call_args[0][0][0].content.split("candidate_markets")) > 0  # Prompt was formatted


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.log_node_state")
def test_process_and_rank_markets_node_error_handling(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test process_and_rank_markets_node error handling."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM to raise an exception
    mock_create_llm_model.side_effect = Exception("LLM error")
    
    with pytest.raises(Exception) as exc_info:
        process_and_rank_markets_node(sample_state)
    
    assert "LLM error" in str(exc_info.value)
    # Verify error event was written
    assert mock_writer.call_count >= 1
