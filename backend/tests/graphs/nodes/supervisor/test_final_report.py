"""
Tests for final_report node.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.supervisor.final_report import final_report_node
from polyplexity_agent.graphs.state import SupervisorState


@pytest.fixture
def sample_state():
    """Create a sample supervisor state."""
    return {
        "user_request": "Research AI",
        "research_notes": ["## Research on: AI\nAI is advancing"],
        "current_report_version": 0,
        "_thread_id": "test_thread",
        "_question_execution_trace": [],
        "answer_format": "concise",
    }


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.save_messages_and_trace")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.log_node_state")
def test_final_report_node(
    mock_log_node_state,
    mock_save_messages,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test final_report_node generates report."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Final report on AI"
    mock_create_llm_model.return_value = mock_llm
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    
    result = final_report_node(sample_state)
    
    assert "final_report" in result
    assert result["final_report"] == "Final report on AI"
    assert result["current_report_version"] == 1
    assert "conversation_history" in result
    # Verify streaming functions were called
    assert mock_stream_trace_event.call_count >= 2  # node_call and custom trace
    assert mock_stream_custom_event.call_count >= 2  # writing_report and final_report_complete


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.save_messages_and_trace")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.log_node_state")
def test_final_report_node_refinement(
    mock_log_node_state,
    mock_save_messages,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test final_report_node handles report refinement."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Refined report"
    mock_create_llm_model.return_value = mock_llm
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    sample_state["final_report"] = "Original report"
    sample_state["current_report_version"] = 1
    
    result = final_report_node(sample_state)
    
    assert result["current_report_version"] == 2
    # Verify refinement prompt was used (check LLM was called)
    mock_create_llm_model.return_value.invoke.assert_called_once()


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.create_llm_model")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.save_messages_and_trace")
@patch("polyplexity_agent.graphs.nodes.supervisor.final_report.log_node_state")
def test_final_report_node_report_format(
    mock_log_node_state,
    mock_save_messages,
    mock_create_trace_event,
    mock_create_llm_model,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test final_report_node uses report format instructions."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Report"
    mock_create_llm_model.return_value = mock_llm
    mock_create_trace_event.side_effect = [
        {"event": "trace", "type": "node_call"},
        {"event": "trace", "type": "custom"},
    ]
    sample_state["answer_format"] = "report"
    
    final_report_node(sample_state)
    
    # Verify LLM was called (format instructions would be different)
    mock_create_llm_model.return_value.invoke.assert_called_once()
