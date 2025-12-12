"""
Integration tests for researcher subgraph.

Tests the complete researcher subgraph flow:
Topic -> Generate Queries -> Parallel Search -> Synthesize Results
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph


@pytest.mark.integration
@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
def test_researcher_subgraph_full_flow(
    mock_synthesize_llm,
    mock_tavily_search,
    mock_generate_llm,
    mock_state_logger,
    sample_researcher_state,
    mock_search_queries,
    mock_tavily_results,
):
    """Test complete researcher subgraph execution flow."""
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_search_queries
    mock_generate_llm.return_value = mock_generate_chain

    mock_tool = Mock()
    mock_tool.invoke.return_value = mock_tavily_results
    mock_tavily_search.return_value = mock_tool

    mock_synthesize_response = Mock()
    mock_synthesize_response.content = "Artificial intelligence (AI) is a branch of computer science..."
    mock_synthesize_chain = Mock()
    mock_synthesize_chain.invoke.return_value = mock_synthesize_response
    mock_synthesize_llm.return_value = mock_synthesize_chain

    result = researcher_graph.invoke(sample_researcher_state)

    assert "research_summary" in result
    assert len(result["research_summary"]) > 0
    assert "queries" in result
    assert len(result["queries"]) == 3
    assert "search_results" in result
    assert len(result["search_results"]) > 0


@pytest.mark.integration
@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
def test_researcher_subgraph_state_accumulation(
    mock_synthesize_llm,
    mock_tavily_search,
    mock_generate_llm,
    mock_state_logger,
    sample_researcher_state,
    mock_search_queries,
    mock_tavily_results,
):
    """Test that search results are properly accumulated."""
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_search_queries
    mock_generate_llm.return_value = mock_generate_chain

    mock_tool = Mock()
    mock_tool.invoke.return_value = mock_tavily_results
    mock_tavily_search.return_value = mock_tool

    mock_synthesize_response = Mock()
    mock_synthesize_response.content = "Synthesized research summary"
    mock_synthesize_chain = Mock()
    mock_synthesize_chain.invoke.return_value = mock_synthesize_response
    mock_synthesize_llm.return_value = mock_synthesize_chain

    result = researcher_graph.invoke(sample_researcher_state)

    assert len(result["search_results"]) >= len(mock_tavily_results["results"])
    assert mock_tavily_search.call_count == len(mock_search_queries.queries)
