"""
Tests for synthesize_research node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.researcher.synthesize_research import synthesize_research_node
from polyplexity_agent.graphs.state import ResearcherState


@pytest.fixture
def sample_state():
    """Create a sample researcher state with search results."""
    return {
        "topic": "artificial intelligence",
        "queries": ["AI definition", "AI applications"],
        "search_results": [
            "--- Results for 'AI definition' ---\nTitle: [AI Overview](https://example.com/ai)\nContent: AI is...\n\n",
            "--- Results for 'AI applications' ---\nTitle: [ML Basics](https://example.com/ml)\nContent: ML is...\n\n",
        ],
        "research_summary": "",
        "query_breadth": 3,
    }


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.log_node_state")
def test_synthesize_research_node(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test synthesize_research_node synthesizes search results."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM response
    mock_response = Mock()
    mock_response.content = "Artificial intelligence (AI) is a branch of computer science..."
    mock_llm_chain = Mock()
    mock_llm_chain.invoke.return_value = mock_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    result = synthesize_research_node(sample_state)
    
    assert "research_summary" in result
    assert len(result["research_summary"]) > 0
    assert "Artificial intelligence" in result["research_summary"]
    assert "execution_trace" in result
    assert len(result["execution_trace"]) == 2
    
    # Verify LLM was called with search results
    invoke_call = mock_llm_chain.invoke
    assert invoke_call.called
    call_args = invoke_call.call_args[0][0]
    assert len(call_args) == 1
    prompt_content = call_args[0].content
    assert "artificial intelligence" in prompt_content.lower()
    assert "AI Overview" in prompt_content or "AI definition" in prompt_content
    
    # Verify events were written
    assert mock_writer.call_count >= 3  # trace events + research_synthesis_done
    
    # Verify log_node_state was called
    assert mock_log_node_state.call_count == 2  # BEFORE and AFTER


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.log_node_state")
def test_synthesize_research_node_multiple_results(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
):
    """Test synthesize_research_node with multiple search results."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    mock_response = Mock()
    mock_response.content = "Comprehensive summary of all research findings..."
    mock_llm_chain = Mock()
    mock_llm_chain.invoke.return_value = mock_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    state = {
        "topic": "quantum computing",
        "queries": ["query1", "query2", "query3"],
        "search_results": [
            "Result 1 content",
            "Result 2 content",
            "Result 3 content",
        ],
        "research_summary": "",
        "query_breadth": 5,
    }
    
    result = synthesize_research_node(state)
    
    assert "research_summary" in result
    assert len(result["research_summary"]) > 0
    
    # Verify all search results were included in prompt
    invoke_call = mock_llm_chain.invoke
    call_args = invoke_call.call_args[0][0]
    prompt_content = call_args[0].content
    assert "Result 1" in prompt_content
    assert "Result 2" in prompt_content
    assert "Result 3" in prompt_content


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.log_node_state")
def test_synthesize_research_node_error_handling(
    mock_log_node_state,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test synthesize_research_node handles errors gracefully."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    # Mock LLM to raise an error
    mock_create_llm_model.side_effect = Exception("LLM API error")
    
    with pytest.raises(Exception, match="LLM API error"):
        synthesize_research_node(sample_state)
    
    # Verify error event was written
    error_calls = [call for call in mock_writer.call_args_list if "error" in str(call)]
    assert len(error_calls) > 0


@patch("polyplexity_agent.graphs.subgraphs.researcher._state_logger")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.researcher.synthesize_research.log_node_state")
def test_synthesize_research_node_empty_results(
    mock_log_node_state,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_get_stream_writer,
    mock_state_logger,
):
    """Test synthesize_research_node handles empty search results."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    
    mock_response = Mock()
    mock_response.content = "No results found."
    mock_llm_chain = Mock()
    mock_llm_chain.invoke.return_value = mock_response
    mock_create_llm_model.return_value = mock_llm_chain
    
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    state = {
        "topic": "test topic",
        "queries": [],
        "search_results": [],
        "research_summary": "",
        "query_breadth": 3,
    }
    
    result = synthesize_research_node(state)
    
    assert "research_summary" in result
    # Even with empty results, LLM should be called and return a summary
    assert mock_create_llm_model.called
