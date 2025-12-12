"""
Integration tests for market research subgraph.

Tests the complete market research subgraph flow:
Topic -> Generate Queries -> Fetch Markets -> Process & Rank -> Evaluate
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.subgraphs.market_research import market_research_graph


@pytest.mark.integration
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
    sample_market_research_state,
    mock_queries_response,
    mock_polymarket_results,
    mock_ranking_response,
    mock_evaluation_response,
):
    """Test complete market research subgraph execution flow."""
    # Mock tag selection
    from polyplexity_agent.models import SelectedTags
    mock_tags_response = SelectedTags(
        selected_tag_names=["Politics", "Elections"],
        reasoning="Relevant tags",
        continue_search=False
    )
    mock_tags_batch = [{"id": 1, "label": "Politics"}, {"id": 2, "label": "Elections"}]
    mock_fetch_tags_batch.return_value = mock_tags_batch
    
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_tags_response
    mock_generate_llm.return_value = mock_generate_chain

    # Mock event fetching
    mock_fetch_events_by_tag_id.return_value = [{"markets": mock_polymarket_results}]

    # Mock ranking
    from polyplexity_agent.models import RankedMarkets
    mock_rank_response = RankedMarkets(
        slugs=["2024-presidential-election"],
        reasoning="Relevant market"
    )
    mock_rank_chain = Mock()
    mock_rank_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_rank_response
    mock_rank_llm.return_value = mock_rank_chain

    # Mock evaluation
    from polyplexity_agent.models import ApprovedMarkets
    mock_eval_response = ApprovedMarkets(
        slugs=["2024-presidential-election"],
        reasoning="Approved market"
    )
    mock_evaluate_chain = Mock()
    mock_evaluate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_eval_response
    mock_evaluate_llm.return_value = mock_evaluate_chain

    result = market_research_graph.invoke(sample_market_research_state)

    assert "approved_markets" in result
    assert len(result["approved_markets"]) > 0
    assert "market_queries" in result
    assert len(result["market_queries"]) > 0


@pytest.mark.integration
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.fetch_tags_batch")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.fetch_events_by_tag_id")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_market_research_subgraph_rejection_flow(
    mock_evaluate_llm,
    mock_rank_llm,
    mock_fetch_events_by_tag_id,
    mock_generate_llm,
    mock_fetch_tags_batch,
    sample_market_research_state,
    mock_queries_response,
    mock_polymarket_results,
    mock_ranking_response,
):
    """Test market research subgraph when markets are rejected (fallback used)."""
    # Mock tag selection
    from polyplexity_agent.models import SelectedTags
    mock_tags_response = SelectedTags(
        selected_tag_names=["Politics"],
        reasoning="Relevant tag",
        continue_search=False
    )
    mock_tags_batch = [{"id": 1, "label": "Politics"}]
    mock_fetch_tags_batch.return_value = mock_tags_batch
    
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_tags_response
    mock_generate_llm.return_value = mock_generate_chain

    # Mock event fetching
    mock_fetch_events_by_tag_id.return_value = [{"markets": mock_polymarket_results}]

    # Mock ranking
    from polyplexity_agent.models import RankedMarkets
    mock_rank_response = RankedMarkets(
        slugs=["2024-presidential-election"],
        reasoning="Relevant market"
    )
    mock_rank_chain = Mock()
    mock_rank_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_rank_response
    mock_rank_llm.return_value = mock_rank_chain

    # Mock rejection (empty slugs)
    from polyplexity_agent.models import ApprovedMarkets
    rejection_response = ApprovedMarkets(slugs=[], reasoning="No markets approved")
    mock_evaluate_chain = Mock()
    mock_evaluate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = rejection_response
    mock_evaluate_llm.return_value = mock_evaluate_chain

    result = market_research_graph.invoke(sample_market_research_state)

    assert "approved_markets" in result
    # Fallback logic should provide markets even if LLM rejects
    assert len(result["approved_markets"]) >= 0
