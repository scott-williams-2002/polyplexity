"""Graph definitions and state management module.

This module contains the main agent graph, state definitions, nodes, and subgraphs.
"""
from .state import MarketResearchState, ResearcherState, SupervisorState

__all__ = [
    "ResearcherState",
    "MarketResearchState",
    "SupervisorState",
    "create_agent_graph",
]


def __getattr__(name: str):
    """
    Lazy import of agent_graph to avoid importing heavy dependencies
    when only state classes are needed.
    
    Args:
        name: Name of the attribute to import
        
    Returns:
        The requested attribute from agent_graph module
        
    Raises:
        AttributeError: If the attribute doesn't exist
    """
    if name == "create_agent_graph":
        from .agent_graph import create_agent_graph
        return create_agent_graph
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
