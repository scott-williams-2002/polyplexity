"""
Tests for agent graph creation and compilation.
"""
from unittest.mock import MagicMock, Mock, patch

import pytest

from polyplexity_agent.config import Settings
from polyplexity_agent.graphs.agent_graph import create_agent_graph


@pytest.fixture
def mock_checkpointer():
    """
    Create a mock checkpointer.
    """
    checkpointer = Mock()
    checkpointer.setup = Mock()
    return checkpointer


@pytest.fixture
def mock_settings():
    """
    Create a mock settings instance.
    """
    settings = Settings()
    return settings


@patch("polyplexity_agent.graphs.agent_graph.supervisor_node")
@patch("polyplexity_agent.graphs.agent_graph.call_researcher_node")
@patch("polyplexity_agent.graphs.agent_graph.final_report_node")
@patch("polyplexity_agent.graphs.agent_graph.direct_answer_node")
@patch("polyplexity_agent.graphs.agent_graph.clarification_node")
@patch("polyplexity_agent.graphs.agent_graph.summarize_conversation_node")
@patch("polyplexity_agent.graphs.agent_graph.route_supervisor")
@patch("polyplexity_agent.graphs.agent_graph.draw_graph")
@patch("polyplexity_agent.graphs.agent_graph.create_checkpointer")
def test_create_agent_graph_with_checkpointer(
    mock_create_checkpointer,
    mock_draw_graph,
    mock_route_supervisor,
    mock_summarize_conversation_node,
    mock_clarification_node,
    mock_direct_answer_node,
    mock_final_report_node,
    mock_call_researcher_node,
    mock_supervisor_node,
    mock_checkpointer,
    mock_settings,
):
    """
    Test that create_agent_graph creates and compiles graph with checkpointer.
    """
    mock_create_checkpointer.return_value = mock_checkpointer
    
    graph = create_agent_graph(settings=mock_settings, checkpointer=mock_checkpointer)
    
    # Verify checkpointer.setup was called
    mock_checkpointer.setup.assert_called_once()
    
    # Verify draw_graph was called
    mock_draw_graph.assert_called_once()
    
    # Verify graph was created
    assert graph is not None


@patch("polyplexity_agent.graphs.agent_graph.supervisor_node")
@patch("polyplexity_agent.graphs.agent_graph.call_researcher_node")
@patch("polyplexity_agent.graphs.agent_graph.final_report_node")
@patch("polyplexity_agent.graphs.agent_graph.direct_answer_node")
@patch("polyplexity_agent.graphs.agent_graph.clarification_node")
@patch("polyplexity_agent.graphs.agent_graph.summarize_conversation_node")
@patch("polyplexity_agent.graphs.agent_graph.route_supervisor")
@patch("polyplexity_agent.graphs.agent_graph.draw_graph")
@patch("polyplexity_agent.graphs.agent_graph.create_checkpointer")
def test_create_agent_graph_without_checkpointer(
    mock_create_checkpointer,
    mock_draw_graph,
    mock_route_supervisor,
    mock_summarize_conversation_node,
    mock_clarification_node,
    mock_direct_answer_node,
    mock_final_report_node,
    mock_call_researcher_node,
    mock_supervisor_node,
):
    """
    Test that create_agent_graph creates and compiles graph without checkpointer.
    """
    mock_create_checkpointer.return_value = None
    
    graph = create_agent_graph(checkpointer=None)
    
    # Verify draw_graph was called
    mock_draw_graph.assert_called_once()
    
    # Verify graph was created
    assert graph is not None


@patch("polyplexity_agent.graphs.agent_graph.supervisor_node")
@patch("polyplexity_agent.graphs.agent_graph.call_researcher_node")
@patch("polyplexity_agent.graphs.agent_graph.final_report_node")
@patch("polyplexity_agent.graphs.agent_graph.direct_answer_node")
@patch("polyplexity_agent.graphs.agent_graph.clarification_node")
@patch("polyplexity_agent.graphs.agent_graph.summarize_conversation_node")
@patch("polyplexity_agent.graphs.agent_graph.route_supervisor")
@patch("polyplexity_agent.graphs.agent_graph.draw_graph")
@patch("polyplexity_agent.graphs.agent_graph.create_checkpointer")
def test_create_agent_graph_default_settings(
    mock_create_checkpointer,
    mock_draw_graph,
    mock_route_supervisor,
    mock_summarize_conversation_node,
    mock_clarification_node,
    mock_direct_answer_node,
    mock_final_report_node,
    mock_call_researcher_node,
    mock_supervisor_node,
):
    """
    Test that create_agent_graph uses default settings when None provided.
    """
    mock_create_checkpointer.return_value = None
    
    graph = create_agent_graph(settings=None, checkpointer=None)
    
    # Verify graph was created
    assert graph is not None
    mock_draw_graph.assert_called_once()


@patch("polyplexity_agent.graphs.agent_graph.supervisor_node")
@patch("polyplexity_agent.graphs.agent_graph.call_researcher_node")
@patch("polyplexity_agent.graphs.agent_graph.final_report_node")
@patch("polyplexity_agent.graphs.agent_graph.direct_answer_node")
@patch("polyplexity_agent.graphs.agent_graph.clarification_node")
@patch("polyplexity_agent.graphs.agent_graph.summarize_conversation_node")
@patch("polyplexity_agent.graphs.agent_graph.route_supervisor")
@patch("polyplexity_agent.graphs.agent_graph.draw_graph")
@patch("polyplexity_agent.graphs.agent_graph.create_checkpointer")
def test_create_agent_graph_checkpointer_setup_failure(
    mock_create_checkpointer,
    mock_draw_graph,
    mock_route_supervisor,
    mock_summarize_conversation_node,
    mock_clarification_node,
    mock_direct_answer_node,
    mock_final_report_node,
    mock_call_researcher_node,
    mock_supervisor_node,
    mock_checkpointer,
):
    """
    Test that create_agent_graph handles checkpointer setup failure gracefully.
    """
    mock_checkpointer.setup.side_effect = Exception("Setup failed")
    mock_create_checkpointer.return_value = mock_checkpointer
    
    # Should not raise exception, but continue without checkpointer
    graph = create_agent_graph(checkpointer=mock_checkpointer)
    
    # Verify graph was still created
    assert graph is not None
    mock_draw_graph.assert_called_once()

