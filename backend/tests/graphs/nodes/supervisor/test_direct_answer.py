"""
Tests for direct_answer node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.supervisor.direct_answer import direct_answer_node
from polyplexity_agent.graphs.state import SupervisorState


@pytest.fixture
def sample_state():
    """Create a sample supervisor state."""
    return {
        "user_request": "What is 2+2?",
        "conversation_summary": "User asking math question",
        "current_report_version": 0,
        "_thread_id": "test_thread",
        "_question_execution_trace": [],
    }


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.save_messages_and_trace")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.log_node_state")
def test_direct_answer_node(
    mock_log_node_state,
    mock_save_messages,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test direct_answer_node generates answer."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "The answer is 4"
    mock_create_llm_model.return_value = mock_llm
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    result = direct_answer_node(sample_state)
    
    assert "final_report" in result
    assert result["final_report"] == "The answer is 4"
    assert result["next_topic"] == "FINISH"
    assert result["current_report_version"] == 1
    assert "conversation_history" in result
    # Verify streaming functions were called
    assert mock_stream_trace_event.call_count >= 2  # node_call and custom trace
    mock_stream_custom_event.assert_called_once()  # final_report_complete


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.save_messages_and_trace")
@patch("polyplexity_agent.graphs.nodes.supervisor.direct_answer.log_node_state")
def test_direct_answer_node_saves_trace(
    mock_log_node_state,
    mock_save_messages,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test direct_answer_node saves messages and trace."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Answer"
    mock_create_llm_model.return_value = mock_llm
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    direct_answer_node(sample_state)
    
    mock_save_messages.assert_called_once()
