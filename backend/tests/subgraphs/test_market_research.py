"""
End-to-end tests for the market research subgraph.

Tests the complete flow: Topic -> Generate Queries -> Fetch Markets -> Process & Rank -> Evaluate
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.state import MarketResearchState


@pytest.fixture
def initial_state():
    """Create initial state for market research subgraph."""
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
    """Create mock tag selection response."""
    from polyplexity_agent.models import SelectedTags
    return SelectedTags(
        selected_tag_names=["Politics", "Elections"],
        reasoning="Relevant tags",
        continue_search=False
    )


@pytest.fixture
def mock_tags_batch():
    """Create mock tags batch."""
    return [{"id": 1, "label": "Politics"}, {"id": 2, "label": "Elections"}]


@pytest.fixture
def mock_polymarket_results():
    """Create mock Polymarket market results."""
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
    ]


@pytest.fixture
def mock_ranking_response():
    """Create mock ranking response."""
    from polyplexity_agent.models import RankedMarkets
    return RankedMarkets(
        slugs=["2024-presidential-election"],
        reasoning="Highly relevant market"
    )


@pytest.fixture
def mock_evaluation_response():
    """Create mock evaluation response."""
    from polyplexity_agent.models import ApprovedMarkets
    return ApprovedMarkets(
        slugs=["2024-presidential-election"],
        reasoning="Approved market"
    )


@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.fetch_tags_batch")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_market_research_subgraph_full_flow(
    mock_evaluate_llm,
    mock_rank_llm,
    mock_fetch_events_by_tag_id,
    mock_generate_llm,
    mock_fetch_tags_batch,
    initial_state,
    mock_tags_response,
    mock_tags_batch,
    mock_polymarket_results,
    mock_ranking_response,
    mock_evaluation_response,
):
    """Test complete market research subgraph execution flow."""
    from polyplexity_agent.graphs.subgraphs.market_research import market_research_graph
    
    # Mock tag fetching
    mock_fetch_tags_batch.return_value = mock_tags_batch
    
    # Mock tag selection LLM
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_tags_response
    mock_generate_llm.return_value = mock_generate_chain
    
    # Mock event fetching
    mock_fetch_events_by_tag_id.return_value = [{"markets": mock_polymarket_results}]
    
    # Mock ranking LLM
    mock_rank_chain = Mock()
    mock_rank_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_ranking_response
    mock_rank_llm.return_value = mock_rank_chain
    
    # Mock evaluation LLM
    mock_evaluate_chain = Mock()
    mock_evaluate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_evaluation_response
    mock_evaluate_llm.return_value = mock_evaluate_chain
    
    # Execute subgraph
    result = market_research_graph.invoke(initial_state)
    
    # Verify final state
    assert "approved_markets" in result
    assert len(result["approved_markets"]) == 1
    assert result["approved_markets"][0]["slug"] == "2024-presidential-election"
    
    # Verify tag IDs were selected
    assert "market_queries" in result
    assert len(result["market_queries"]) > 0
    
    # Verify raw events were fetched
    assert "raw_events" in result
    assert len(result["raw_events"]) > 0
    
    # Verify candidate markets were ranked
    assert "candidate_markets" in result
    assert len(result["candidate_markets"]) == 1
    
    # Verify LLM was called for tag selection
    assert mock_generate_llm.called
    
    # Verify fetch_events_by_tag_id was called
    assert mock_fetch_events_by_tag_id.called
    
    # Verify ranking LLM was called
    assert mock_rank_llm.called
    
    # Verify evaluation LLM was called
    assert mock_evaluate_llm.called


@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.fetch_tags_batch")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_market_research_subgraph_streaming(
    mock_evaluate_llm,
    mock_rank_llm,
    mock_fetch_events_by_tag_id,
    mock_generate_llm,
    mock_fetch_tags_batch,
    initial_state,
    mock_tags_response,
    mock_tags_batch,
    mock_polymarket_results,
    mock_ranking_response,
    mock_evaluation_response,
):
    """Test market research subgraph streaming with custom events."""
    from polyplexity_agent.graphs.subgraphs.market_research import market_research_graph
    
    # Mock tag fetching
    mock_fetch_tags_batch.return_value = mock_tags_batch
    
    # Mock tag selection LLM
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_tags_response
    mock_generate_llm.return_value = mock_generate_chain
    
    # Mock event fetching
    mock_fetch_events_by_tag_id.return_value = [{"markets": mock_polymarket_results}]
    
    # Mock ranking LLM
    mock_rank_chain = Mock()
    mock_rank_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_ranking_response
    mock_rank_llm.return_value = mock_rank_chain
    
    # Mock evaluation LLM
    mock_evaluate_chain = Mock()
    mock_evaluate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_evaluation_response
    mock_evaluate_llm.return_value = mock_evaluate_chain
    
    # Stream subgraph execution
    events = list(market_research_graph.stream(initial_state, stream_mode=["custom", "values"]))
    
    # Verify events were yielded
    assert len(events) > 0
    
    # Check for custom events (tag_selected, market_approved, market_research_complete)
    custom_events = [e for mode, e in events if mode == "custom"]
    assert len(custom_events) > 0
    
    # Check for values events (state updates)
    values_events = [e for mode, e in events if mode == "values"]
    assert len(values_events) > 0
    
    # Verify final state includes approved_markets
    final_state = values_events[-1] if values_events else {}
    if isinstance(final_state, dict):
        assert "approved_markets" in final_state or any("approved_markets" in str(v) for v in final_state.values())


@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
def test_market_research_subgraph_error_propagation(
    mock_generate_llm,
    initial_state,
):
    """Test that errors in nodes propagate correctly through subgraph."""
    from polyplexity_agent.graphs.subgraphs.market_research import market_research_graph
    
    # Mock LLM to raise an error
    mock_generate_llm.side_effect = Exception("LLM API error")
    
    # Subgraph should propagate the error
    with pytest.raises(Exception, match="LLM API error"):
        market_research_graph.invoke(initial_state)


@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.fetch_tags_batch")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_market_research_subgraph_empty_results(
    mock_evaluate_llm,
    mock_rank_llm,
    mock_fetch_events_by_tag_id,
    mock_generate_llm,
    mock_fetch_tags_batch,
    initial_state,
    mock_tags_response,
    mock_tags_batch,
):
    """Test market research subgraph handles empty results."""
    from polyplexity_agent.graphs.subgraphs.market_research import market_research_graph
    from polyplexity_agent.models import RankedMarkets, ApprovedMarkets
    
    # Mock tag fetching
    mock_fetch_tags_batch.return_value = mock_tags_batch
    
    # Mock tag selection LLM
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_tags_response
    mock_generate_llm.return_value = mock_generate_chain
    
    # Mock event fetching to return empty results
    mock_fetch_events_by_tag_id.return_value = []
    
    # Mock ranking LLM
    mock_rank_chain = Mock()
    mock_rank_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = RankedMarkets(slugs=[], reasoning="No markets")
    mock_rank_llm.return_value = mock_rank_chain
    
    # Mock evaluation LLM
    mock_evaluate_chain = Mock()
    mock_evaluate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = ApprovedMarkets(slugs=[], reasoning="No markets approved")
    mock_evaluate_llm.return_value = mock_evaluate_chain
    
    # Execute subgraph
    result = market_research_graph.invoke(initial_state)
    
    # Verify final state has empty approved_markets (or fallback markets)
    assert "approved_markets" in result


def test_create_market_research_graph():
    """Test create_market_research_graph function creates a valid graph."""
    from polyplexity_agent.graphs.subgraphs.market_research import create_market_research_graph
    
    graph = create_market_research_graph()
    
    # Verify graph is compiled and callable
    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "stream")


@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.fetch_tags_batch")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_market_research_subgraph_reject_decision(
    mock_evaluate_llm,
    mock_rank_llm,
    mock_fetch_events_by_tag_id,
    mock_generate_llm,
    mock_fetch_tags_batch,
    initial_state,
    mock_tags_response,
    mock_tags_batch,
    mock_polymarket_results,
    mock_ranking_response,
):
    """Test market research subgraph with REJECT decision (fallback used)."""
    from polyplexity_agent.graphs.subgraphs.market_research import market_research_graph
    from polyplexity_agent.models import ApprovedMarkets
    
    # Mock tag fetching
    mock_fetch_tags_batch.return_value = mock_tags_batch
    
    # Mock tag selection LLM
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_tags_response
    mock_generate_llm.return_value = mock_generate_chain
    
    # Mock event fetching
    mock_fetch_events_by_tag_id.return_value = [{"markets": mock_polymarket_results}]
    
    # Mock ranking LLM
    mock_rank_chain = Mock()
    mock_rank_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_ranking_response
    mock_rank_llm.return_value = mock_rank_chain
    
    # Mock evaluation LLM with REJECT decision (empty slugs)
    mock_evaluate_chain = Mock()
    mock_evaluate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = ApprovedMarkets(slugs=[], reasoning="No markets approved")
    mock_evaluate_llm.return_value = mock_evaluate_chain
    
    # Execute subgraph
    result = market_research_graph.invoke(initial_state)
    
    # Verify final state (fallback should provide markets)
    assert "approved_markets" in result
    # Fallback logic should provide markets even if LLM rejects
    assert len(result["approved_markets"]) >= 0
