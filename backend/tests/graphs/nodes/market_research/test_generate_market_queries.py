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
def mock_tags_response():
    """Create a mock tag selection response."""
    from polyplexity_agent.models import SelectedTags
    return SelectedTags(
        selected_tag_names=["Politics", "Elections", "US Politics"],
        reasoning="These tags are relevant to the election topic.",
        continue_search=False
    )


@pytest.fixture
def mock_tags_batch():
    """Create a mock tags batch from API."""
    return [
        {"id": 1, "label": "Politics", "slug": "politics"},
        {"id": 2, "label": "Elections", "slug": "elections"},
        {"id": 3, "label": "US Politics", "slug": "us-politics"},
        {"id": 4, "label": "Sports", "slug": "sports"},
    ]


@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.fetch_tags_batch")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
def test_generate_market_queries_node(
    mock_create_llm_model,
    mock_stream_custom_event,
    mock_fetch_tags_batch,
    sample_state,
    mock_tags_response,
    mock_tags_batch,
):
    """Test generate_market_queries_node selects tags successfully."""
    
    # Mock tag batch fetch
    mock_fetch_tags_batch.return_value = mock_tags_batch
    
    # Mock LLM chain
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_tags_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    result = generate_market_queries_node(sample_state)
    
    assert "market_queries" in result
    assert len(result["market_queries"]) == 3  # Should have 3 tag IDs
    assert "reasoning_trace" in result
    assert "execution_trace" not in result  # Removed in new implementation
    
    # Verify tag_selected event was streamed
    tag_selected_calls = [call for call in mock_stream_custom_event.call_args_list 
                         if call[0][0] == "tag_selected"]
    assert len(tag_selected_calls) == 1
    assert "tags" in tag_selected_calls[0][0][2]


@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.fetch_tags_batch")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
def test_generate_market_queries_node_different_topics(
    mock_create_llm_model,
    mock_stream_custom_event,
    mock_fetch_tags_batch,
    mock_tags_response,
    mock_tags_batch,
):
    """Test generate_market_queries_node with different topics."""
    
    mock_fetch_tags_batch.return_value = mock_tags_batch
    
    mock_llm_chain = Mock()
    mock_llm_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_tags_response
    mock_create_llm_model.return_value = mock_llm_chain
    
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


@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
def test_generate_market_queries_node_error_handling(
    mock_create_llm_model,
    mock_stream_custom_event,
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
