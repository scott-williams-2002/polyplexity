"""
Tests for fetch_markets node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.market_research.fetch_markets import fetch_markets_node
from polyplexity_agent.graphs.state import MarketResearchState


@pytest.fixture
def sample_state():
    """Create a sample market research state."""
    return {
        "original_topic": "2024 US presidential election",
        "market_queries": ["2024 election", "presidential race"],
        "raw_events": [],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }


@pytest.fixture
def mock_polymarket_results():
    """Create mock Polymarket search results."""
    return [
        {
            "title": "2024 Presidential Election",
            "slug": "2024-presidential-election",
            "description": "Who will win the 2024 US presidential election?",
            "markets": [],
        },
        {
            "title": "Election Predictions",
            "slug": "election-predictions",
            "description": "Predictions for the 2024 election",
            "markets": [],
        },
        {
            "title": "2024 Presidential Election",  # Duplicate slug
            "slug": "2024-presidential-election",
            "description": "Duplicate event",
            "markets": [],
        },
    ]


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.search_markets")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.log_node_state")
def test_fetch_markets_node(
    mock_log_node_state,
    mock_create_trace_event,
    mock_search_markets,
    mock_stream_trace_event,
    mock_state_logger,
    sample_state,
    mock_polymarket_results,
):
    """Test fetch_markets_node fetches and deduplicates markets successfully."""
    
    # Mock search_markets to return results for each query
    mock_search_markets.side_effect = [
        mock_polymarket_results[:2],  # First query returns 2 events
        mock_polymarket_results[1:],  # Second query returns 2 events (1 duplicate)
    ]
    
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = fetch_markets_node(sample_state)
    
    assert "raw_events" in result
    assert len(result["raw_events"]) == 2  # Should deduplicate to 2 unique events
    assert "reasoning_trace" in result
    assert "execution_trace" in result
    
    # Verify deduplication worked
    slugs = [event["slug"] for event in result["raw_events"]]
    assert len(slugs) == len(set(slugs))  # All slugs should be unique
    
    # Verify search_markets was called for each query
    assert mock_search_markets.call_count == 2
    
    # Verify log_node_state was called
    assert mock_log_node_state.call_count == 2  # BEFORE and AFTER


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.search_markets")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.log_node_state")
def test_fetch_markets_node_empty_results(
    mock_log_node_state,
    mock_create_trace_event,
    mock_search_markets,
    mock_stream_trace_event,
    mock_state_logger,
    sample_state,
):
    """Test fetch_markets_node handles empty results."""
    
    # Mock search_markets to return empty results
    mock_search_markets.return_value = []
    
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = fetch_markets_node(sample_state)
    
    assert "raw_events" in result
    assert len(result["raw_events"]) == 0
    assert "reasoning_trace" in result


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.search_markets")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.log_node_state")
def test_fetch_markets_node_error_handling(
    mock_log_node_state,
    mock_create_trace_event,
    mock_search_markets,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test fetch_markets_node error handling."""
    # Mock search_markets to raise an exception
    mock_search_markets.side_effect = Exception("API error")
    
    with pytest.raises(Exception) as exc_info:
        fetch_markets_node(sample_state)
    
    assert "API error" in str(exc_info.value)
    # Verify error event was streamed
    mock_stream_custom_event.assert_called_once()
    call_args = mock_stream_custom_event.call_args
    assert call_args[0][0] == "error"  # event_name
    assert call_args[0][1] == "fetch_markets"  # node


@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.search_markets")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.log_node_state")
def test_fetch_markets_node_multiple_queries(
    mock_log_node_state,
    mock_create_trace_event,
    mock_search_markets,
    mock_stream_trace_event,
    mock_state_logger,
    mock_polymarket_results,
):
    """Test fetch_markets_node with multiple queries."""
    
    state = {
        "original_topic": "test topic",
        "market_queries": ["query1", "query2", "query3"],
        "raw_events": [],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }
    
    # Mock search_markets to return different results for each query
    mock_search_markets.side_effect = [
        [mock_polymarket_results[0]],
        [mock_polymarket_results[1]],
        [mock_polymarket_results[0]],  # Duplicate
    ]
    
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = fetch_markets_node(state)
    
    # Should have 2 unique events (duplicate removed)
    assert len(result["raw_events"]) == 2
    assert mock_search_markets.call_count == 3
