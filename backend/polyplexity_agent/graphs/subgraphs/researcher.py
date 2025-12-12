"""
Researcher subgraph implementation.

Handles focused research workflow: Topic -> Generate Queries -> Parallel Search -> Synthesize Results
"""
from typing import Optional

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from polyplexity_agent.graphs.nodes.researcher import (
    generate_queries_node,
    perform_search_node,
    synthesize_research_node,
)
from polyplexity_agent.graphs.state import ResearcherState

# Global state logger instance (temporary, like Phase 4 pattern)
_state_logger: Optional[object] = None


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


def map_queries(state: ResearcherState):
    """Maps queries to parallel search node invocations."""
    breadth = state.get("query_breadth", 2)
    return [Send("perform_search", {"query": q, "query_breadth": breadth}) for q in state["queries"]]


def build_researcher_subgraph():
    """Build and compile the researcher subgraph."""
    builder = StateGraph(ResearcherState)
    builder.add_node("generate_queries", generate_queries_node)
    builder.add_node("perform_search", perform_search_node)
    builder.add_node("synthesize_research", synthesize_research_node)
    
    builder.add_edge(START, "generate_queries")
    builder.add_conditional_edges("generate_queries", map_queries, ["perform_search"])
    builder.add_edge("perform_search", "synthesize_research")
    builder.add_edge("synthesize_research", END)
    
    return builder.compile()


def create_researcher_graph():
    """Create the researcher subgraph (alias for build_researcher_subgraph)."""
    return build_researcher_subgraph()


# Compile the subgraph at module level
researcher_graph = build_researcher_subgraph()
