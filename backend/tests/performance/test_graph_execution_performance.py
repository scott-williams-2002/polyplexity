"""
Performance tests for graph execution.

Measures graph execution time and identifies bottlenecks.
"""
import time
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.agent_graph import create_agent_graph


@pytest.mark.slow
@pytest.mark.performance
@patch("polyplexity_agent.graphs.agent_graph.create_checkpointer")
def test_graph_creation_performance(mock_create_checkpointer, mock_settings):
    """Test that graph creation is fast."""
    mock_checkpointer = Mock()
    mock_create_checkpointer.return_value = mock_checkpointer

    start_time = time.time()
    graph = create_agent_graph(settings=mock_settings, checkpointer=mock_checkpointer)
    end_time = time.time()

    assert graph is not None
    assert (end_time - start_time) < 5.0


@pytest.mark.slow
@pytest.mark.performance
def test_graph_creation_without_checkpointer_performance(mock_settings):
    """Test graph creation performance without checkpointer."""
    start_time = time.time()
    graph = create_agent_graph(settings=mock_settings, checkpointer=None)
    end_time = time.time()

    assert graph is not None
    assert (end_time - start_time) < 3.0
