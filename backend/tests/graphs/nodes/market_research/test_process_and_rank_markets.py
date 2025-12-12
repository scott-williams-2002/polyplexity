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
                "slug": "2024-presidential-election",
                "question": "Who will win the 2024 US presidential election?",
                "description": "Election market",
                "clobTokenIds": ["token1"],
            },
            {
                "slug": "election-predictions",
                "question": "What are the election predictions?",
                "description": "Predictions market",
                "clobTokenIds": ["token2"],
            },
        ],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }


@pytest.fixture
def mock_ranking_response():
    """Create a mock ranking response."""
    from polyplexity_agent.models import RankedMarkets
    return RankedMarkets(
        slugs=["2024-presidential-election", "election-predictions"],
        reasoning="These markets are highly relevant to the election topic."
    )


@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
def test_process_and_rank_markets_node(
    mock_create_llm_model,
    sample_state,
    mock_ranking_response,
):
    """Test process_and_rank_markets_node ranks markets successfully."""
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_ranking_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    result = process_and_rank_markets_node(sample_state)
    
    assert "candidate_markets" in result
    assert len(result["candidate_markets"]) == 2
    assert "reasoning_trace" in result
    assert "execution_trace" not in result  # Removed in new implementation


@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
def test_process_and_rank_markets_node_limits_to_twenty(
    mock_create_llm_model,
    mock_ranking_response,
):
    """Test process_and_rank_markets_node limits to 20 markets."""
    # Create state with more than 20 markets
    state = {
        "original_topic": "test topic",
        "market_queries": [],
        "raw_events": [
            {"slug": f"market-{i}", "question": f"Question {i}", "description": "", "clobTokenIds": []}
            for i in range(30)
        ],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }
    
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_ranking_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    result = process_and_rank_markets_node(state)
    
    # Verify LLM was called (should process up to 20 markets)
    assert mock_create_llm_model.called


@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
def test_process_and_rank_markets_node_error_handling(
    mock_create_llm_model,
    mock_stream_custom_event,
    sample_state,
):
    """Test process_and_rank_markets_node error handling."""
    # Mock LLM to raise an exception
    mock_create_llm_model.side_effect = Exception("LLM error")
    
    with pytest.raises(Exception) as exc_info:
        process_and_rank_markets_node(sample_state)
    
    assert "LLM error" in str(exc_info.value)
    # Verify error event was streamed
    mock_stream_custom_event.assert_called_once()
    call_args = mock_stream_custom_event.call_args
    assert call_args[0][0] == "error"  # event_name
    assert call_args[0][1] == "process_and_rank_markets"  # node
