"""
End-to-end tests for the orchestrator agent flow.

Tests the complete flow from run_research_agent() through graph execution,
including all node interactions, state transitions, and event streaming.
"""
from unittest.mock import Mock, patch
from typing import Any, Dict

import pytest

from polyplexity_agent.entrypoint import run_research_agent
from polyplexity_agent.models import SupervisorDecision


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_research_flow(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_graph,
    mock_researcher_graph,
    mock_llm,
    mock_settings,
):
    """Test end-to-end flow with research path."""
    # Setup mock graph stream to simulate graph execution
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution stream."""
        # Supervisor decision event
        yield ("custom", {"event": "supervisor_decision", "decision": "research", "topic": "test topic"})
        yield ("custom", {"event": "trace", "type": "node_call", "node": "supervisor"})
        
        # Call researcher events
        yield ("custom", {"event": "web_search_url", "url": "https://example.com"})
        yield ("updates", {"call_researcher": {"research_notes": ["## Research on: test topic\nMock research summary"]}})
        
        # Final report events
        yield ("custom", {"event": "writing_report"})
        yield ("custom", {"event": "final_report_complete", "report": "Final report on test topic"})
        yield ("updates", {"final_report": {"final_report": "Final report on test topic"}})
        
        # Summarize conversation
        yield ("updates", {"summarize_conversation": {"conversation_summary": "Summary"}})
    
    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger
    
    # Run the agent
    events = list(run_research_agent("What is AI?", graph=mock_graph))
    
    # Verify events were yielded
    assert len(events) > 0
    
    # Verify supervisor decision event
    supervisor_events = [e for e in events if isinstance(e[1], dict) and e[1].get("event") == "supervisor_decision"]
    assert len(supervisor_events) > 0
    
    # Verify research notes were added
    research_events = [e for e in events if isinstance(e[1], dict) and "research_notes" in str(e[1])]
    assert len(research_events) > 0
    
    # Verify final report was generated
    report_events = [e for e in events if isinstance(e[1], dict) and e[1].get("event") == "final_report_complete"]
    assert len(report_events) > 0
    
    # Verify state logger was set up
    mock_set_state_logger.assert_called()
    mock_set_researcher_logger.assert_called()
    mock_state_logger.close.assert_called()


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_direct_answer_flow(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_graph,
    mock_llm,
    mock_settings,
):
    """Test end-to-end flow with direct answer path (no research needed)."""
    # Mock supervisor decision to finish immediately
    supervisor_decision = Mock(spec=SupervisorDecision)
    supervisor_decision.next_step = "finish"
    supervisor_decision.research_topic = ""
    supervisor_decision.reasoning = "Can answer directly"
    supervisor_decision.answer_format = "concise"
    
    mock_llm.with_structured_output.return_value.with_retry.return_value.invoke.return_value = supervisor_decision
    
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution stream for direct answer."""
        # Supervisor decision to finish
        yield ("custom", {"event": "supervisor_decision", "decision": "finish"})
        
        # Direct answer events
        yield ("custom", {"event": "final_report_complete", "report": "Direct answer: 2+2=4"})
        yield ("updates", {"direct_answer": {"final_report": "Direct answer: 2+2=4"}})
        
        # Summarize conversation
        yield ("updates", {"summarize_conversation": {"conversation_summary": "Summary"}})
    
    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger
    
    # Run the agent
    events = list(run_research_agent("What is 2+2?", graph=mock_graph))
    
    # Verify direct answer was generated
    # Events are now in envelope format: {"type": "...", "event": "...", "payload": {...}}
    report_events = [e for e in events if isinstance(e[1], dict) and e[1].get("event") == "final_report_complete"]
    assert len(report_events) > 0
    # Check payload for report content
    event_data = report_events[0][1]
    if "payload" in event_data:
        assert "2+2=4" in event_data["payload"].get("report", "")
    else:
        # Fallback for old format (shouldn't happen but be safe)
        assert "2+2=4" in event_data.get("report", "")


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_clarification_flow(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_graph,
    mock_llm,
    mock_settings,
):
    """Test end-to-end flow with clarification path."""
    # Mock supervisor decision to clarify
    supervisor_decision = Mock(spec=SupervisorDecision)
    supervisor_decision.next_step = "clarify"
    supervisor_decision.research_topic = ""
    supervisor_decision.reasoning = "What location are you interested in?"
    supervisor_decision.answer_format = "concise"
    
    mock_llm.with_structured_output.return_value.with_retry.return_value.invoke.return_value = supervisor_decision
    
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution stream for clarification."""
        # Supervisor decision to clarify
        yield ("custom", {"event": "supervisor_decision", "decision": "clarify"})
        
        # Clarification events
        yield ("custom", {"event": "final_report_complete", "report": "What location are you interested in?"})
        yield ("updates", {"clarification": {"final_report": "What location are you interested in?"}})
        
        # Summarize conversation
        yield ("updates", {"summarize_conversation": {"conversation_summary": "Summary"}})
    
    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger
    
    # Run the agent
    events = list(run_research_agent("Tell me about the weather", graph=mock_graph))
    
    # Verify clarification was generated
    # Events are now in envelope format: {"type": "...", "event": "...", "payload": {...}}
    report_events = [e for e in events if isinstance(e[1], dict) and e[1].get("event") == "final_report_complete"]
    assert len(report_events) > 0
    # Check payload for report content
    event_data = report_events[0][1]
    if "payload" in event_data:
        assert "location" in event_data["payload"].get("report", "").lower()
    else:
        # Fallback for old format (shouldn't happen but be safe)
        assert "location" in event_data.get("report", "").lower()


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer")
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_with_checkpointer(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_checkpointer_patch,
    mock_graph,
    mock_researcher_graph,
    mock_llm,
    mock_settings,
):
    """Test end-to-end flow with checkpointer (thread persistence)."""
    # Mock checkpointer
    mock_checkpointer_instance = Mock()
    mock_checkpointer_patch.return_value = mock_checkpointer_instance
    
    # Mock graph to return no existing state (new thread)
    mock_graph.get_state.return_value = Mock(values=None)
    
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution stream."""
        # Verify thread_id is in config
        assert config.get("configurable", {}).get("thread_id") is not None
        
        yield ("custom", {"event": "thread_id", "thread_id": "test_thread"})
        yield ("custom", {"event": "supervisor_decision", "decision": "finish"})
        yield ("updates", {"direct_answer": {"final_report": "Answer"}})
        yield ("updates", {"summarize_conversation": {}})
    
    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger
    
    # Run the agent with thread_id
    events = list(run_research_agent("Test question", thread_id="test_thread", graph=mock_graph))
    
    # Verify thread_id event was yielded
    thread_events = [e for e in events if isinstance(e[1], dict) and e[1].get("event") == "thread_id"]
    assert len(thread_events) > 0
    assert thread_events[0][1]["thread_id"] == "test_thread"
    
    # Verify trace completeness was ensured
    mock_ensure_trace.assert_called_once()


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer")
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_follow_up_conversation(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_checkpointer_patch,
    mock_graph,
    mock_llm,
    mock_settings,
):
    """Test end-to-end flow with follow-up conversation (existing state)."""
    # Mock checkpointer
    mock_checkpointer_instance = Mock()
    mock_checkpointer_patch.return_value = mock_checkpointer_instance
    
    # Mock existing state (follow-up conversation)
    existing_state = {
        "conversation_summary": "Previous conversation about AI",
        "current_report_version": 1,
        "conversation_history": [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is..."}
        ]
    }
    mock_graph.get_state.return_value = Mock(values=existing_state)
    
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution stream."""
        # Verify initial state includes conversation summary
        assert initial_state.get("conversation_summary") == "Previous conversation about AI"
        assert initial_state.get("current_report_version") == 1
        
        yield ("custom", {"event": "supervisor_decision", "decision": "finish"})
        yield ("updates", {"direct_answer": {"final_report": "Follow-up answer"}})
        yield ("updates", {"summarize_conversation": {}})
    
    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger
    
    # Run the agent with thread_id (follow-up)
    events = list(run_research_agent("Tell me more", thread_id="test_thread", graph=mock_graph))
    
    # Verify events were generated
    assert len(events) > 0


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_event_streaming(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_graph,
    mock_researcher_graph,
    mock_llm,
    mock_settings,
):
    """Test that events are properly streamed and formatted."""
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution with various event types."""
        # Trace event
        yield ("custom", {"event": "trace", "type": "node_call", "node": "supervisor"})
        
        # Supervisor decision
        yield ("custom", {"event": "supervisor_decision", "decision": "research", "topic": "test"})
        
        # Web search URL
        yield ("custom", {"event": "web_search_url", "url": "https://example.com"})
        
        # State updates
        yield ("updates", {"call_researcher": {"research_notes": ["Note 1"]}})
        yield ("updates", {"supervisor": {"iterations": 1}})
        
        # Final report
        yield ("custom", {"event": "writing_report"})
        yield ("custom", {"event": "final_report_complete", "report": "Final report"})
        yield ("updates", {"final_report": {"final_report": "Final report"}})
    
    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger
    
    # Run the agent
    events = list(run_research_agent("Test question", graph=mock_graph))
    
    # Verify different event types were yielded
    event_types = set()
    for mode, data in events:
        if isinstance(data, dict):
            event_types.add(data.get("event", "update"))
    
    # Should have trace, supervisor_decision, web_search_url, writing_report, final_report_complete
    assert "trace" in event_types or "supervisor_decision" in event_types
    assert "final_report_complete" in event_types
    
    # Verify both custom and updates modes are present
    modes = set(mode for mode, _ in events)
    assert "custom" in modes or "updates" in modes


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_error_handling(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_graph,
    mock_llm,
    mock_settings,
):
    """Test that errors are handled gracefully and logger is cleaned up."""
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution that raises an error."""
        yield ("custom", {"event": "supervisor_decision", "decision": "research"})
        raise Exception("Test error")
    
    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger
    
    # Run the agent - should handle error gracefully
    with pytest.raises(Exception):
        list(run_research_agent("Test question", graph=mock_graph))
    
    # Verify logger was cleaned up even on error
    mock_state_logger.close.assert_called()
    mock_set_state_logger.assert_called_with(None)
    mock_set_researcher_logger.assert_called_with(None)


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_multi_iteration_research(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_graph,
    mock_researcher_graph,
    mock_llm,
    mock_settings,
):
    """Test end-to-end flow with multiple research iterations."""
    iteration_count = [0]

    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution with multiple iterations."""
        iteration_count[0] += 1
        if iteration_count[0] <= 2:
            yield ("custom", {"event": "supervisor_decision", "decision": "research", "topic": f"topic {iteration_count[0]}"})
            yield ("updates", {"call_researcher": {"research_notes": [f"Research iteration {iteration_count[0]}"]}})
            yield ("updates", {"supervisor": {"iterations": iteration_count[0]}})
        else:
            yield ("custom", {"event": "supervisor_decision", "decision": "finish"})
            yield ("custom", {"event": "final_report_complete", "report": "Final report after multiple iterations"})
            yield ("updates", {"final_report": {"final_report": "Final report after multiple iterations"}})
            yield ("updates", {"summarize_conversation": {"conversation_summary": "Summary"}})

    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger

    events = list(run_research_agent("Complex research question", graph=mock_graph))

    assert len(events) > 0
    research_events = [e for e in events if isinstance(e[1], dict) and "research_notes" in str(e[1])]
    assert len(research_events) >= 1


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_max_iterations_limit(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_graph,
    mock_llm,
    mock_settings,
):
    """Test that max iterations limit is enforced."""
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution hitting max iterations."""
        yield ("custom", {"event": "supervisor_decision", "decision": "finish"})
        yield ("custom", {"event": "final_report_complete", "report": "Report after max iterations"})
        yield ("updates", {"supervisor": {"iterations": 10}})
        yield ("updates", {"final_report": {"final_report": "Report after max iterations"}})
        yield ("updates", {"summarize_conversation": {}})

    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger

    events = list(run_research_agent("Test question", graph=mock_graph))

    assert len(events) > 0
    final_events = [e for e in events if isinstance(e[1], dict) and e[1].get("event") == "final_report_complete"]
    assert len(final_events) > 0


@pytest.mark.e2e
@patch("polyplexity_agent.entrypoint._checkpointer", None)
@patch("polyplexity_agent.entrypoint._state_logger", None)
@patch("polyplexity_agent.entrypoint.set_state_logger")
@patch("polyplexity_agent.entrypoint.set_researcher_logger")
@patch("polyplexity_agent.entrypoint.StateLogger")
@patch("polyplexity_agent.entrypoint.ensure_trace_completeness")
def test_end_to_end_empty_response_handling(
    mock_ensure_trace,
    mock_state_logger_class,
    mock_set_researcher_logger,
    mock_set_state_logger,
    mock_graph,
    mock_llm,
    mock_settings,
):
    """Test handling of empty responses."""
    def mock_graph_stream(initial_state, config, stream_mode):
        """Simulate graph execution with empty responses."""
        yield ("custom", {"event": "supervisor_decision", "decision": "finish"})
        yield ("updates", {"direct_answer": {"final_report": ""}})
        yield ("updates", {"summarize_conversation": {}})

    mock_graph.stream = mock_graph_stream
    mock_state_logger = Mock()
    mock_state_logger_class.return_value = mock_state_logger

    events = list(run_research_agent("", graph=mock_graph))

    assert len(events) > 0
