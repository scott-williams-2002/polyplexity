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
    """Create mock Polymarket event results."""
    return [
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
        {
            "slug": "2024-presidential-election",  # Duplicate slug
            "question": "Duplicate market",
            "description": "Duplicate",
            "clobTokenIds": ["token3"],
        },
    ]


@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
def test_fetch_markets_node(
    mock_fetch_events_by_tag_id,
    sample_state,
    mock_polymarket_results,
):
    """Test fetch_markets_node fetches and deduplicates markets successfully."""
    
    # Mock fetch_events_by_tag_id to return results for each tag ID
    mock_fetch_events_by_tag_id.side_effect = [
        [{"markets": mock_polymarket_results[:2]}],  # First tag returns 2 markets
        [{"markets": mock_polymarket_results[1:]}],  # Second tag returns 2 markets (1 duplicate)
    ]
    
    result = fetch_markets_node(sample_state)
    
    assert "raw_events" in result
    assert len(result["raw_events"]) == 2  # Should deduplicate to 2 unique markets
    assert "reasoning_trace" in result
    assert "execution_trace" not in result  # Removed in new implementation
    
    # Verify deduplication worked
    slugs = [market["slug"] for market in result["raw_events"]]
    assert len(slugs) == len(set(slugs))  # All slugs should be unique
    
    # Verify fetch_events_by_tag_id was called for each tag ID
    assert mock_fetch_events_by_tag_id.call_count == 2


@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
def test_fetch_markets_node_empty_results(
    mock_fetch_events_by_tag_id,
    sample_state,
):
    """Test fetch_markets_node handles empty results."""
    
    # Mock fetch_events_by_tag_id to return empty results
    mock_fetch_events_by_tag_id.return_value = []
    
    result = fetch_markets_node(sample_state)
    
    assert "raw_events" in result
    assert len(result["raw_events"]) == 0
    assert "reasoning_trace" in result


@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
def test_fetch_markets_node_error_handling(
    mock_fetch_events_by_tag_id,
    mock_stream_custom_event,
    sample_state,
):
    """Test fetch_markets_node error handling."""
    # Mock fetch_events_by_tag_id to raise an exception
    mock_fetch_events_by_tag_id.side_effect = Exception("API error")
    
    with pytest.raises(Exception) as exc_info:
        fetch_markets_node(sample_state)
    
    assert "API error" in str(exc_info.value)
    # Verify error event was streamed
    mock_stream_custom_event.assert_called_once()
    call_args = mock_stream_custom_event.call_args
    assert call_args[0][0] == "error"  # event_name
    assert call_args[0][1] == "fetch_markets"  # node


@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
def test_fetch_markets_node_multiple_queries(
    mock_fetch_events_by_tag_id,
    mock_polymarket_results,
):
    """Test fetch_markets_node with multiple tag IDs."""
    
    state = {
        "original_topic": "test topic",
        "market_queries": ["tag1", "tag2", "tag3"],
        "raw_events": [],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }
    
    # Mock fetch_events_by_tag_id to return different results for each tag ID
    mock_fetch_events_by_tag_id.side_effect = [
        [{"markets": [mock_polymarket_results[0]]}],
        [{"markets": [mock_polymarket_results[1]]}],
        [{"markets": [mock_polymarket_results[0]]}],  # Duplicate
    ]
    
    result = fetch_markets_node(state)
    
    # Should have 2 unique markets (duplicate removed)
    assert len(result["raw_events"]) == 2
    assert mock_fetch_events_by_tag_id.call_count == 3
