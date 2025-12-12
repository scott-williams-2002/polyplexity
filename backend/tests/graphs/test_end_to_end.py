"""
End-to-end tests for the orchestrator agent flow.

Tests the complete flow from run_research_agent() through graph execution,
including all node interactions, state transitions, and event streaming.
"""
from unittest.mock import MagicMock, Mock, patch
from typing import Any, Dict, Iterator, Tuple

import pytest

from polyplexity_agent.entrypoint import run_research_agent
from polyplexity_agent.graphs.agent_graph import create_agent_graph
from polyplexity_agent.models import SupervisorDecision


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    from polyplexity_agent.config import Settings
    settings = Settings()
    # Use a temporary directory for state logs
    import tempfile
    settings.state_logs_dir = tempfile.mkdtemp()
    return settings


@pytest.fixture
def mock_graph(mock_settings):
    """Create a mock graph for testing."""
    with patch("polyplexity_agent.entrypoint.create_default_graph") as mock_create:
        graph = Mock()
        graph.stream = Mock()
        graph.get_state = Mock(return_value=None)
        mock_create.return_value = graph
        yield graph


@pytest.fixture
def mock_researcher_graph():
    """Mock the researcher subgraph."""
    def mock_stream(input_state, stream_mode):
        """Mock researcher graph stream."""
        # Yield custom events
        yield ("custom", [{"event": "web_search_url", "url": "https://example.com"}])
        # Yield values with research summary
        yield ("values", {"research_summary": "Mock research summary about the topic"})
    
    with patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.researcher_graph") as mock_researcher:
        mock_researcher.stream = mock_stream
        yield mock_researcher


@pytest.fixture
def mock_llm():
    """Mock LLM responses."""
    mock_llm_instance = Mock()
    
    # Mock supervisor decision
    supervisor_decision = Mock(spec=SupervisorDecision)
    supervisor_decision.next_step = "research"
    supervisor_decision.research_topic = "test topic"
    supervisor_decision.reasoning = "Need to research"
    supervisor_decision.answer_format = "concise"
    
    # Mock LLM chain
    mock_chain = Mock()
    mock_chain.invoke.return_value.content = "Mock LLM response"
    mock_chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = supervisor_decision
    
    mock_llm_instance.with_structured_output.return_value.with_retry.return_value.invoke.return_value = supervisor_decision
    mock_llm_instance.invoke.return_value.content = "Mock LLM response"
    
    with patch("polyplexity_agent.utils.helpers.create_llm_model", return_value=mock_llm_instance):
        yield mock_llm_instance


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
    report_events = [e for e in events if isinstance(e[1], dict) and e[1].get("event") == "final_report_complete"]
    assert len(report_events) > 0
    assert "2+2=4" in report_events[0][1]["report"]


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
    report_events = [e for e in events if isinstance(e[1], dict) and e[1].get("event") == "final_report_complete"]
    assert len(report_events) > 0
    assert "location" in report_events[0][1]["report"].lower()


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
