"""
Tests for perform_search node.
"""
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def sample_state():
    """Create a sample state for perform_search node."""
    return {
        "query": "artificial intelligence",
        "query_breadth": 3,
    }


@pytest.fixture
def mock_tavily_results():
    """Create mock Tavily search results."""
    return {
        "results": [
            {
                "title": "AI Overview",
                "url": "https://example.com/ai",
                "content": "Artificial intelligence is...",
            },
            {
                "title": "Machine Learning Basics",
                "url": "https://example.com/ml",
                "content": "Machine learning is a subset of AI...",
            },
        ]
    }


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.log_node_state")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.format_search_url_markdown")
def test_perform_search_node(
    mock_format_markdown,
    mock_log_node_state,
    mock_create_trace_event,
    mock_tavily_search,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
    mock_tavily_results,
):
    """Test perform_search_node executes search and formats results."""
    
    # Mock TavilySearch tool
    mock_tool = Mock()
    mock_tool.invoke.return_value = mock_tavily_results
    mock_tavily_search.return_value = mock_tool
    
    mock_format_markdown.side_effect = lambda url: f"[{url}]({url})"
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "search"},
        {"event": "trace", "type": "search"},
    ]
    
    from polyplexity_agent.graphs.nodes.researcher.perform_search import perform_search_node
    
    result = perform_search_node(sample_state)
    
    assert "search_results" in result
    assert len(result["search_results"]) == 1
    assert "artificial intelligence" in result["search_results"][0]
    assert "AI Overview" in result["search_results"][0]
    assert "execution_trace" in result
    assert len(result["execution_trace"]) == 3
    
    # Verify TavilySearch was called with correct max_results
    mock_tavily_search.assert_called_once_with(max_results=3, topic="general")
    mock_tool.invoke.assert_called_once_with({"query": "artificial intelligence"})
    
    # Verify web_search_url events were emitted
    url_calls = [
        call for call in mock_stream_custom_event.call_args_list
        if call[0][0] == "web_search_url"
    ]
    assert len(url_calls) == 2  # Two URLs in results


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.log_node_state")
def test_perform_search_node_query_breadth_default(
    mock_log_node_state,
    mock_create_trace_event,
    mock_tavily_search,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    mock_tavily_results,
):
    """Test perform_search_node defaults query_breadth to 2 if missing."""
    
    mock_tool = Mock()
    mock_tool.invoke.return_value = mock_tavily_results
    mock_tavily_search.return_value = mock_tool
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "search"},
        {"event": "trace", "type": "search"},
    ]
    
    from polyplexity_agent.graphs.nodes.researcher.perform_search import perform_search_node
    
    state = {
        "query": "test query",
        # query_breadth missing
    }
    
    perform_search_node(state)
    
    # Verify TavilySearch was called with default max_results=2
    mock_tavily_search.assert_called_once_with(max_results=2, topic="general")


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.streaming.stream_writer.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.log_node_state")
def test_perform_search_node_error_handling(
    mock_log_node_state,
    mock_tavily_search,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test perform_search_node handles errors gracefully."""
    # Mock get_stream_writer to return None (no runtime context in tests)
    mock_get_stream_writer.return_value = None
    
    # Mock TavilySearch to raise an error
    mock_tavily_search.side_effect = Exception("Tavily API error")
    
    from polyplexity_agent.graphs.nodes.researcher.perform_search import perform_search_node
    
    with pytest.raises(Exception, match="Tavily API error"):
        perform_search_node(sample_state)
    
    # Verify error event was streamed
    error_calls = [call for call in mock_stream_custom_event.call_args_list if call[0][0] == "error"]
    assert len(error_calls) >= 1


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.log_node_state")
@patch("polyplexity_agent.graphs.nodes.researcher.perform_search.format_search_url_markdown")
def test_perform_search_node_empty_results(
    mock_format_markdown,
    mock_log_node_state,
    mock_create_trace_event,
    mock_tavily_search,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test perform_search_node handles empty search results."""
    
    mock_tool = Mock()
    mock_tool.invoke.return_value = {"results": []}
    mock_tavily_search.return_value = mock_tool
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "search"},
        {"event": "trace", "type": "search"},
    ]
    
    from polyplexity_agent.graphs.nodes.researcher.perform_search import perform_search_node
    
    result = perform_search_node(sample_state)
    
    assert "search_results" in result
    assert len(result["search_results"]) == 1
    assert "artificial intelligence" in result["search_results"][0]
    
    # Verify no web_search_url events were emitted
    url_calls = [
        call for call in mock_stream_custom_event.call_args_list
        if call[0][0] == "web_search_url"
    ]
    assert len(url_calls) == 0
