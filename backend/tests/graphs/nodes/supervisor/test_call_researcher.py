"""
Tests for call_researcher node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.supervisor.call_researcher import call_researcher_node
from polyplexity_agent.graphs.state import SupervisorState


@pytest.fixture
def sample_state():
    """Create a sample supervisor state."""
    return {
        "user_request": "Research AI",
        "next_topic": "AI research",
        "answer_format": "concise",
        "iterations": 0,
        "research_notes": [],
    }


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.stream_trace_event")
@patch("langgraph.config.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.researcher_graph")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.log_node_state")
def test_call_researcher_node(
    mock_log_node_state,
    mock_create_trace_event,
    mock_researcher_graph,
    mock_get_stream_writer,
    mock_stream_trace_event,
    mock_state_logger,
    sample_state,
):
    """Test call_researcher_node invokes researcher subgraph."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    # Mock researcher_graph.stream to yield custom and values
    def mock_stream(input_state, stream_mode):
        yield ("custom", [{"event": "web_search_url", "url": "https://example.com"}])
        yield ("values", {"research_summary": "AI is advancing rapidly"})
    
    mock_researcher_graph.stream = mock_stream
    
    result = call_researcher_node(sample_state)
    
    assert "research_notes" in result
    assert len(result["research_notes"]) == 1
    assert "AI research" in result["research_notes"][0]
    assert "execution_trace" in result
    mock_writer.assert_called()


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.stream_trace_event")
@patch("langgraph.config.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.researcher_graph")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.log_node_state")
def test_call_researcher_node_url_deduplication(
    mock_log_node_state,
    mock_create_trace_event,
    mock_researcher_graph,
    mock_get_stream_writer,
    mock_stream_trace_event,
    mock_state_logger,
    sample_state,
):
    """Test call_researcher_node deduplicates web_search_url events."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    def mock_stream(input_state, stream_mode):
        yield ("custom", [{"event": "web_search_url", "url": "https://example.com"}])
        yield ("custom", [{"event": "web_search_url", "url": "https://example.com"}])
        yield ("values", {"research_summary": "Summary"})
    
    mock_researcher_graph.stream = mock_stream
    
    call_researcher_node(sample_state)
    
    # Should only write URL once
    url_writes = [call for call in mock_writer.call_args_list if "url" in str(call)]
    assert len(url_writes) == 1


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.stream_trace_event")
@patch("langgraph.config.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.researcher_graph")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.log_node_state")
def test_call_researcher_node_breadth_concise(
    mock_log_node_state,
    mock_create_trace_event,
    mock_researcher_graph,
    mock_get_stream_writer,
    mock_stream_trace_event,
    mock_state_logger,
    sample_state,
):
    """Test call_researcher_node uses correct breadth for concise format."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    sample_state["answer_format"] = "concise"
    
    def mock_stream(input_state, stream_mode):
        assert input_state["query_breadth"] == 3
        yield ("values", {"research_summary": "Summary"})
    
    mock_researcher_graph.stream = mock_stream
    
    call_researcher_node(sample_state)


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.stream_trace_event")
@patch("langgraph.config.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.researcher_graph")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.log_node_state")
def test_call_researcher_node_breadth_report(
    mock_log_node_state,
    mock_create_trace_event,
    mock_researcher_graph,
    mock_get_stream_writer,
    mock_stream_trace_event,
    mock_state_logger,
    sample_state,
):
    """Test call_researcher_node uses correct breadth for report format."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    sample_state["answer_format"] = "report"
    
    def mock_stream(input_state, stream_mode):
        assert input_state["query_breadth"] == 5
        yield ("values", {"research_summary": "Summary"})
    
    mock_researcher_graph.stream = mock_stream
    
    call_researcher_node(sample_state)
