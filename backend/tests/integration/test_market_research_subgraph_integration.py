"""
Integration tests for market research subgraph.

Tests the complete market research subgraph flow:
Topic -> Generate Queries -> Fetch Markets -> Process & Rank -> Evaluate
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.subgraphs.market_research import market_research_graph


@pytest.mark.integration
@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.search_markets")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_market_research_subgraph_full_flow(
    mock_evaluate_llm,
    mock_rank_llm,
    mock_search_markets,
    mock_generate_llm,
    mock_state_logger,
    sample_market_research_state,
    mock_queries_response,
    mock_polymarket_results,
    mock_ranking_response,
    mock_evaluation_response,
):
    """Test complete market research subgraph execution flow."""
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.invoke.return_value = mock_queries_response
    mock_generate_llm.return_value = mock_generate_chain

    mock_search_markets.side_effect = [
        mock_polymarket_results,
        mock_polymarket_results,
        mock_polymarket_results,
    ]

    mock_rank_chain = Mock()
    mock_rank_chain.with_structured_output.return_value.invoke.return_value = mock_ranking_response
    mock_rank_llm.return_value = mock_rank_chain

    mock_evaluate_chain = Mock()
    mock_evaluate_chain.with_structured_output.return_value.invoke.return_value = mock_evaluation_response
    mock_evaluate_llm.return_value = mock_evaluate_chain

    result = market_research_graph.invoke(sample_market_research_state)

    assert "approved_markets" in result
    assert len(result["approved_markets"]) > 0
    assert "market_queries" in result
    assert len(result["market_queries"]) > 0


@pytest.mark.integration
@patch("polyplexity_agent.graphs.subgraphs.market_research._state_logger")
@patch("polyplexity_agent.graphs.nodes.market_research.generate_market_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.search_markets")
@patch("polyplexity_agent.graphs.nodes.market_research.process_and_rank_markets.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.market_research.evaluate_markets.create_llm_model")
def test_market_research_subgraph_rejection_flow(
    mock_evaluate_llm,
    mock_rank_llm,
    mock_search_markets,
    mock_generate_llm,
    mock_state_logger,
    sample_market_research_state,
    mock_queries_response,
    mock_polymarket_results,
    mock_ranking_response,
):
    """Test market research subgraph when markets are rejected."""
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.invoke.return_value = mock_queries_response
    mock_generate_llm.return_value = mock_generate_chain

    mock_search_markets.return_value = mock_polymarket_results

    mock_rank_chain = Mock()
    mock_rank_chain.with_structured_output.return_value.invoke.return_value = mock_ranking_response
    mock_rank_llm.return_value = mock_rank_chain

    rejection_response = {"decision": "REJECT", "markets": []}
    mock_evaluate_chain = Mock()
    mock_evaluate_chain.with_structured_output.return_value.invoke.return_value = rejection_response
    mock_evaluate_llm.return_value = mock_evaluate_chain

    result = market_research_graph.invoke(sample_market_research_state)

    assert "approved_markets" in result
    assert len(result["approved_markets"]) == 0
