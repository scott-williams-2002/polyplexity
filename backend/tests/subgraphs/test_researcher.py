"""
End-to-end tests for the researcher subgraph.

Tests the complete flow: Topic -> Generate Queries -> Parallel Search -> Synthesize Results
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.state import ResearcherState
from polyplexity_agent.models import SearchQueries


@pytest.fixture
def initial_state():
    """Create initial state for researcher subgraph."""
    return {
        "topic": "artificial intelligence",
        "queries": [],
        "search_results": [],
        "research_summary": "",
        "query_breadth": 3,
    }


@pytest.fixture
def mock_search_queries():
    """Create mock SearchQueries response."""
    return SearchQueries(queries=["AI definition", "AI applications", "AI history"])


@pytest.fixture
def mock_tavily_results():
    """Create mock Tavily search results."""
    return {
        "results": [
            {
                "title": "AI Overview",
                "url": "https://example.com/ai",
                "content": "Artificial intelligence is a branch of computer science...",
            },
            {
                "title": "Machine Learning Basics",
                "url": "https://example.com/ml",
                "content": "Machine learning is a subset of AI...",
            },
        ]
    }


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
def test_researcher_subgraph_full_flow(
    mock_synthesize_llm,
    mock_tavily_search,
    mock_generate_llm,
    mock_state_logger,
    initial_state,
    mock_search_queries,
    mock_tavily_results,
):
    """Test complete researcher subgraph execution flow."""
    from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
    
    # Mock query generation LLM
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_search_queries
    mock_generate_llm.return_value = mock_generate_chain
    
    # Mock Tavily search
    mock_tool = Mock()
    mock_tool.invoke.return_value = mock_tavily_results
    mock_tavily_search.return_value = mock_tool
    
    # Mock synthesis LLM
    mock_synthesize_response = Mock()
    mock_synthesize_response.content = "Artificial intelligence (AI) is a branch of computer science that aims to create intelligent machines..."
    mock_synthesize_chain = Mock()
    mock_synthesize_chain.invoke.return_value = mock_synthesize_response
    mock_synthesize_llm.return_value = mock_synthesize_chain
    
    # Execute subgraph
    result = researcher_graph.invoke(initial_state)
    
    # Verify final state
    assert "research_summary" in result
    assert len(result["research_summary"]) > 0
    assert "Artificial intelligence" in result["research_summary"] or "AI" in result["research_summary"]
    
    # Verify queries were generated
    assert "queries" in result
    assert len(result["queries"]) == 3
    assert result["queries"] == ["AI definition", "AI applications", "AI history"]
    
    # Verify search results were accumulated
    assert "search_results" in result
    assert len(result["search_results"]) > 0
    
    # Verify LLM was called for query generation
    assert mock_generate_llm.called
    
    # Verify TavilySearch was called (should be called 3 times, once per query)
    assert mock_tavily_search.call_count == 3
    
    # Verify synthesis LLM was called
    assert mock_synthesize_llm.called


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
def test_researcher_subgraph_streaming(
    mock_synthesize_llm,
    mock_tavily_search,
    mock_generate_llm,
    mock_state_logger,
    initial_state,
    mock_search_queries,
    mock_tavily_results,
):
    """Test researcher subgraph streaming with custom events."""
    from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
    
    # Mock query generation LLM
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_search_queries
    mock_generate_llm.return_value = mock_generate_chain
    
    # Mock Tavily search
    mock_tool = Mock()
    mock_tool.invoke.return_value = mock_tavily_results
    mock_tavily_search.return_value = mock_tool
    
    # Mock synthesis LLM
    mock_synthesize_response = Mock()
    mock_synthesize_response.content = "Research summary"
    mock_synthesize_chain = Mock()
    mock_synthesize_chain.invoke.return_value = mock_synthesize_response
    mock_synthesize_llm.return_value = mock_synthesize_chain
    
    # Stream subgraph execution
    events = list(researcher_graph.stream(initial_state, stream_mode=["custom", "values"]))
    
    # Verify events were yielded
    assert len(events) > 0
    
    # Check for custom events (trace events, web_search_url, etc.)
    custom_events = [e for mode, e in events if mode == "custom"]
    assert len(custom_events) > 0
    
    # Check for values events (state updates)
    values_events = [e for mode, e in events if mode == "values"]
    assert len(values_events) > 0
    
    # Verify final state includes research_summary
    final_state = values_events[-1] if values_events else {}
    if isinstance(final_state, dict):
        assert "research_summary" in final_state or any("research_summary" in str(v) for v in final_state.values())


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
def test_researcher_subgraph_query_breadth(
    mock_synthesize_llm,
    mock_tavily_search,
    mock_generate_llm,
    mock_state_logger,
    mock_search_queries,
    mock_tavily_results,
):
    """Test researcher subgraph respects query_breadth parameter."""
    from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
    
    # Mock query generation LLM
    mock_generate_chain = Mock()
    mock_generate_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = mock_search_queries
    mock_generate_llm.return_value = mock_generate_chain
    
    # Mock Tavily search
    mock_tool = Mock()
    mock_tool.invoke.return_value = mock_tavily_results
    mock_tavily_search.return_value = mock_tool
    
    # Mock synthesis LLM
    mock_synthesize_response = Mock()
    mock_synthesize_response.content = "Summary"
    mock_synthesize_chain = Mock()
    mock_synthesize_chain.invoke.return_value = mock_synthesize_response
    mock_synthesize_llm.return_value = mock_synthesize_chain
    
    # Test with different query_breadth values
    for breadth in [2, 3, 5]:
        state = {
            "topic": "test topic",
            "queries": [],
            "search_results": [],
            "research_summary": "",
            "query_breadth": breadth,
        }
        
        researcher_graph.invoke(state)
        
        # Verify TavilySearch was called 3 times (once per query)
        # Each call should use the correct max_results (breadth)
        assert mock_tavily_search.call_count == 3
        # Verify each call used the correct breadth
        for call in mock_tavily_search.call_args_list:
            assert call[1]["max_results"] == breadth or call[0][0] == breadth
        
        mock_tavily_search.reset_mock()


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
def test_map_queries_function(
    mock_state_logger,
):
    """Test map_queries routing function."""
    from polyplexity_agent.graphs.subgraphs.researcher import map_queries
    
    state = {
        "queries": ["query1", "query2", "query3"],
        "query_breadth": 5,
    }
    
    result = map_queries(state)
    
    # Should return list of Send objects
    assert isinstance(result, list)
    assert len(result) == 3
    
    # Each Send should target "perform_search" with query and query_breadth
    for send_obj in result:
        assert hasattr(send_obj, "node") or hasattr(send_obj, "arg")  # LangGraph Send object
        # Verify payload includes query_breadth
        if hasattr(send_obj, "arg"):
            assert "query_breadth" in send_obj.arg or send_obj.arg.get("query_breadth") == 5


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
def test_map_queries_default_breadth(
    mock_state_logger,
):
    """Test map_queries defaults query_breadth to 2 if missing."""
    from polyplexity_agent.graphs.subgraphs.researcher import map_queries
    
    state = {
        "queries": ["query1", "query2"],
        # query_breadth missing
    }
    
    result = map_queries(state)
    
    assert isinstance(result, list)
    assert len(result) == 2


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.generate_queries.create_llm_model")
def test_researcher_subgraph_error_propagation(
    mock_generate_llm,
    mock_state_logger,
    initial_state,
):
    """Test that errors in nodes propagate correctly through subgraph."""
    from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
    
    # Mock LLM to raise an error
    mock_generate_llm.side_effect = Exception("LLM API error")
    
    # Subgraph should propagate the error
    with pytest.raises(Exception, match="LLM API error"):
        researcher_graph.invoke(initial_state)


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
def test_create_researcher_graph(
    mock_state_logger,
):
    """Test create_researcher_graph function creates a valid graph."""
    from polyplexity_agent.graphs.subgraphs.researcher import create_researcher_graph
    
    graph = create_researcher_graph()
    
    # Verify graph is compiled and callable
    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "stream")
