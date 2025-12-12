"""Subgraph definitions module.

This module contains subgraph definitions for researcher and market research.
"""
from polyplexity_agent.graphs.subgraphs.market_research import (
    create_market_research_graph,
    market_research_graph,
    set_state_logger as set_market_research_logger,
)
from polyplexity_agent.graphs.subgraphs.researcher import (
    create_researcher_graph,
    researcher_graph,
    set_state_logger,
)

__all__ = [
    "create_researcher_graph",
    "researcher_graph",
    "set_state_logger",
    "create_market_research_graph",
    "market_research_graph",
    "set_market_research_logger",
]
