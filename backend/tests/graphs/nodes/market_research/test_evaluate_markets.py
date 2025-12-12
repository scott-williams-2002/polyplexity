"""
Tests for evaluate_markets node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.market_research.evaluate_markets import evaluate_markets_node
from polyplexity_agent.graphs.state import MarketResearchState


@pytest.fixture
def sample_state():
    """Create a sample market research state."""
    return {
        "original_topic": "2024 US presidential election",
        "market_queries": ["2024 election"],
        "raw_events": [],
        "candidate_markets": [
            {
                "slug": "2024-presidential-election",
                "question": "Who will win the 2024 US presidential election?",
                "description": "This market resolves based on the official election results.",
                "clobTokenIds": ["token1", "token2"],
            },
            {
                "slug": "election-predictions",
                "question": "What are the election predictions?",
                "description": "Predictions for the election",
                "clobTokenIds": ["token3"],
            },
        ],
        "approved_markets": [],
        "reasoning_trace": [],
    }


@pytest.fixture
def mock_approve_response():
    """Create a mock approve evaluation response."""
    from polyplexity_agent.models import ApprovedMarkets
    return ApprovedMarkets(
        slugs=["2024-presidential-election"],
        reasoning="This market is highly relevant to the 2024 US presidential election topic."
    )


@pytest.fixture
def mock_reject_response():
    """Create a mock reject evaluation response."""
    from polyplexity_agent.models import ApprovedMarkets
    return ApprovedMarkets(
        slugs=[],
        reasoning="No markets meet the quality standards."
    )


@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_evaluate_markets_node_approve(
    mock_create_llm_model,
    mock_stream_custom_event,
    sample_state,
    mock_approve_response,
):
    """Test evaluate_markets_node with APPROVE decision."""
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_approve_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    result = evaluate_markets_node(sample_state)
    
    assert "approved_markets" in result
    assert len(result["approved_markets"]) == 1
    assert "reasoning_trace" in result
    assert "execution_trace" not in result  # Removed in new implementation
    
    # Verify market_approved event was streamed
    market_approved_calls = [call for call in mock_stream_custom_event.call_args_list 
                            if call[0][0] == "market_approved"]
    assert len(market_approved_calls) == 1
    
    # Verify market_research_complete event was streamed
    complete_calls = [call for call in mock_stream_custom_event.call_args_list 
                     if call[0][0] == "market_research_complete"]
    assert len(complete_calls) == 1
    assert "reasoning" in complete_calls[0][0][2]


@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_evaluate_markets_node_reject(
    mock_create_llm_model,
    mock_stream_custom_event,
    sample_state,
    mock_reject_response,
):
    """Test evaluate_markets_node with REJECT decision (fallback markets)."""
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_reject_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    result = evaluate_markets_node(sample_state)
    
    assert "approved_markets" in result
    # Fallback logic should use top markets if LLM returns empty
    assert len(result["approved_markets"]) > 0  # Fallback markets should be used
    
    # Verify fallback markets were streamed
    market_approved_calls = [call for call in mock_stream_custom_event.call_args_list 
                            if call[0][0] == "market_approved"]
    assert len(market_approved_calls) > 0  # Fallback markets should be streamed


@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_evaluate_markets_node_error_handling(
    mock_create_llm_model,
    mock_stream_custom_event,
    sample_state,
):
    """Test evaluate_markets_node error handling."""
    # Mock LLM to raise an exception
    mock_create_llm_model.side_effect = Exception("LLM error")
    
    with pytest.raises(Exception) as exc_info:
        evaluate_markets_node(sample_state)
    
    assert "LLM error" in str(exc_info.value)
    # Verify error event was streamed
    mock_stream_custom_event.assert_called_once()
    call_args = mock_stream_custom_event.call_args
    assert call_args[0][0] == "error"  # event_name
    assert call_args[0][1] == "evaluate_markets"  # node
