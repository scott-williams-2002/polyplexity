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
        "approved_markets": [],
        "reasoning_trace": [],
    }


@pytest.fixture
def mock_approve_response():
    """Create a mock approve evaluation response."""
    return {
        "decision": "APPROVE",
        "markets": [
            {
                "title": "2024 Presidential Election",
                "slug": "2024-presidential-election",
                "description": "Who will win?",
                "markets": [],
            },
        ],
    }


@pytest.fixture
def mock_reject_response():
    """Create a mock reject evaluation response."""
    return {
        "decision": "REJECT",
        "markets": [],
    }


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.log_node_state")
def test_evaluate_markets_node_approve(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
    mock_approve_response,
):
    """Test evaluate_markets_node with APPROVE decision."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.invoke.return_value = mock_approve_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = evaluate_markets_node(sample_state)
    
    assert "approved_markets" in result
    assert len(result["approved_markets"]) == 1
    assert "reasoning_trace" in result
    assert "execution_trace" in result
    assert "APPROVE" in result["reasoning_trace"][0]
    
    # Verify log_node_state was called
    assert mock_log_node_state.call_count == 2  # BEFORE and AFTER


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.log_node_state")
def test_evaluate_markets_node_reject(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
    mock_reject_response,
):
    """Test evaluate_markets_node with REJECT decision."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.invoke.return_value = mock_reject_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = evaluate_markets_node(sample_state)
    
    assert "approved_markets" in result
    assert len(result["approved_markets"]) == 0  # Should be empty on reject
    assert "REJECT" in result["reasoning_trace"][0]


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.log_node_state")
def test_evaluate_markets_node_error_handling(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test evaluate_markets_node error handling."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM to raise an exception
    mock_create_llm_model.side_effect = Exception("LLM error")
    
    with pytest.raises(Exception) as exc_info:
        evaluate_markets_node(sample_state)
    
    assert "LLM error" in str(exc_info.value)
    # Verify error event was written
    assert mock_writer.call_count >= 1
