"""
Tests for clarification node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.supervisor.clarification import clarification_node
from polyplexity_agent.graphs.state import SupervisorState


@pytest.fixture
def sample_state():
    """Create a sample supervisor state."""
    return {
        "user_request": "Tell me about it",
        "next_topic": "CLARIFY:What location are you interested in?",
        "current_report_version": 0,
        "_thread_id": "test_thread",
        "_question_execution_trace": [],
    }


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.clarification.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.supervisor.clarification.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.clarification.save_messages_and_trace")
@patch("polyplexity_agent.graphs.nodes.supervisor.clarification.log_node_state")
def test_clarification_node(
    mock_log_node_state,
    mock_save_messages,
    mock_create_trace_event,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test clarification_node generates clarification question."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = clarification_node(sample_state)
    
    assert "final_report" in result
    assert "What location" in result["final_report"]
    assert result["next_topic"] == "FINISH"
    assert "conversation_history" in result
    mock_writer.assert_called()


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.clarification.get_stream_writer")
@patch("polyplexity_agent.graphs.nodes.supervisor.clarification.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.clarification.save_messages_and_trace")
@patch("polyplexity_agent.graphs.nodes.supervisor.clarification.log_node_state")
def test_clarification_node_default_question(
    mock_log_node_state,
    mock_save_messages,
    mock_create_trace_event,
    mock_get_stream_writer,
    mock_state_logger,
    sample_state,
):
    """Test clarification_node uses default question when no CLARIFY prefix."""
    mock_writer = Mock()
    mock_get_stream_writer.return_value = mock_writer
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    sample_state["next_topic"] = "FINISH"
    
    result = clarification_node(sample_state)
    
    assert "Could you please clarify your request?" in result["final_report"]
