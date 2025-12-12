"""
Supervisor nodes for the main agent graph.

This module contains all supervisor node implementations.
"""
# Import summarize_conversation first to avoid circular import with state.py
# This must be imported first because state.py imports manage_chat_history from here
from polyplexity_agent.graphs.nodes.supervisor.summarize_conversation import (
    manage_chat_history,
    summarize_conversation_node,
)

# Lazy imports for other nodes to avoid circular dependencies
# These will be imported on-demand via __getattr__

__all__ = [
    "supervisor_node",
    "call_researcher_node",
    "direct_answer_node",
    "clarification_node",
    "final_report_node",
    "summarize_conversation_node",
    "manage_chat_history",
]


def __getattr__(name: str):
    """Lazy import of supervisor nodes to avoid circular dependencies."""
    if name == "supervisor_node":
        from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node
        return supervisor_node
    elif name == "call_researcher_node":
        from polyplexity_agent.graphs.nodes.supervisor.call_researcher import call_researcher_node
        return call_researcher_node
    elif name == "direct_answer_node":
        from polyplexity_agent.graphs.nodes.supervisor.direct_answer import direct_answer_node
        return direct_answer_node
    elif name == "clarification_node":
        from polyplexity_agent.graphs.nodes.supervisor.clarification import clarification_node
        return clarification_node
    elif name == "final_report_node":
        from polyplexity_agent.graphs.nodes.supervisor.final_report import final_report_node
        return final_report_node
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
