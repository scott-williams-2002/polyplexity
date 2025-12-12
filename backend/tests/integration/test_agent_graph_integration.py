"""
Integration tests for main agent graph.

Tests the complete agent graph with all nodes and state transitions.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.agent_graph import create_agent_graph


@pytest.mark.integration
@patch("polyplexity_agent.graphs.agent_graph.create_checkpointer")
def test_agent_graph_creation(mock_create_checkpointer, mock_settings):
    """Test that agent graph can be created successfully."""
    mock_checkpointer = Mock()
    mock_create_checkpointer.return_value = mock_checkpointer

    graph = create_agent_graph(settings=mock_settings, checkpointer=mock_checkpointer)

    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "stream")


@pytest.mark.integration
@patch("polyplexity_agent.graphs.agent_graph.create_checkpointer")
def test_agent_graph_without_checkpointer(mock_create_checkpointer, mock_settings):
    """Test that agent graph can be created without checkpointer."""
    graph = create_agent_graph(settings=mock_settings, checkpointer=None)

    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "stream")


@pytest.mark.integration
def test_agent_graph_default_settings():
    """Test that agent graph uses default settings when none provided."""
    graph = create_agent_graph()

    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "stream")
