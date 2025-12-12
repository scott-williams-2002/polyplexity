"""
Tests for supervisor node.
"""
from unittest.mock import MagicMock, Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.models import SupervisorDecision


@pytest.fixture
def sample_state():
    """Create a sample supervisor state."""
    return {
        "user_request": "What is the weather?",
        "research_notes": [],
        "iterations": 0,
        "conversation_history": [],
        "conversation_summary": "",
        "next_topic": "",
        "final_report": "",
        "answer_format": "concise",
    }


@pytest.fixture
def mock_decision():
    """Create a mock supervisor decision."""
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "research"
    decision.research_topic = "weather information"
    decision.reasoning = "Need to research weather"
    decision.answer_format = "concise"
    return decision


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor._make_supervisor_decision")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.log_node_state")
def test_supervisor_node_research_decision(
    mock_log_node_state,
    mock_create_trace_event,
    mock_make_decision,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
    mock_decision,
):
    """Test supervisor node with research decision."""
    mock_make_decision.return_value = mock_decision
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = supervisor_node(sample_state)
    
    assert "next_topic" in result
    assert result["next_topic"] == "weather information"
    assert result["iterations"] == 1
    assert "execution_trace" in result
    # Verify streaming functions were called
    assert mock_stream_trace_event.call_count >= 2  # node_call and reasoning
    mock_stream_custom_event.assert_called_once()  # supervisor_decision


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor._make_supervisor_decision")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.log_node_state")
def test_supervisor_node_finish_decision(
    mock_log_node_state,
    mock_create_trace_event,
    mock_make_decision,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test supervisor node with finish decision."""
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "finish"
    decision.research_topic = "done"
    decision.reasoning = "Have enough info"
    decision.answer_format = "concise"
    mock_make_decision.return_value = decision
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = supervisor_node(sample_state)
    
    assert result["next_topic"] == "FINISH"
    assert result["iterations"] == 0


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor._make_supervisor_decision")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.log_node_state")
def test_supervisor_node_clarify_decision(
    mock_log_node_state,
    mock_create_trace_event,
    mock_make_decision,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test supervisor node with clarify decision."""
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "clarify"
    decision.research_topic = "need clarification"
    decision.reasoning = "What location?"
    decision.answer_format = "concise"
    mock_make_decision.return_value = decision
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    
    result = supervisor_node(sample_state)
    
    assert result["next_topic"].startswith("CLARIFY:")
    assert "What location?" in result["next_topic"]


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor._handle_thread_name_generation")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.log_node_state")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor._make_supervisor_decision")
def test_supervisor_node_thread_name_generation(
    mock_make_decision,
    mock_log_node_state,
    mock_create_trace_event,
    mock_handle_thread_name,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
    mock_decision,
):
    """Test supervisor node generates thread name on first iteration."""
    mock_make_decision.return_value = mock_decision
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    sample_state["_thread_id"] = "test_thread"
    
    supervisor_node(sample_state)
    
    mock_handle_thread_name.assert_called_once()


@patch("polyplexity_agent.orchestrator._state_logger")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_custom_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.stream_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.create_trace_event")
@patch("polyplexity_agent.graphs.nodes.supervisor.supervisor.log_node_state")
def test_supervisor_node_max_iterations(
    mock_log_node_state,
    mock_create_trace_event,
    mock_stream_trace_event,
    mock_stream_custom_event,
    mock_state_logger,
    sample_state,
):
    """Test supervisor node enforces max iterations limit."""
    mock_create_trace_event.return_value = {"event": "trace", "type": "node_call"}
    sample_state["iterations"] = 10
    
    result = supervisor_node(sample_state)
    
    assert result["next_topic"] == "FINISH"
    # Verify streaming functions were called
    mock_stream_trace_event.assert_called_once()  # node_call
    mock_stream_custom_event.assert_called_once()  # supervisor_log
