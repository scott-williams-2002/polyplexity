"""
Researcher subgraph implementation.
This subgraph handles focused research on a specific topic:
Topic -> Generate Queries -> Parallel Search -> Synthesize Results
"""
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from .states import ResearcherState
from .researcher_nodes import (
    generate_queries_node,
    perform_search_node,
    synthesize_research_node,
)


def map_queries(state: ResearcherState):
    """
    Maps queries to parallel search node invocations.
    
    This function is used with conditional edges to create parallel
    execution of search operations for each query.
    
    Args:
        state: ResearcherState containing the queries list
        
    Returns:
        List of Send objects for parallel execution
    """
    return [Send("perform_search", {"query": q}) for q in state["queries"]]


def build_researcher_subgraph():
    """
    Build and compile the researcher subgraph.
    
    Graph flow:
    START -> generate_queries -> [parallel: perform_search] -> synthesize_research -> END
    
    Returns:
        Compiled LangGraph subgraph ready for invocation
    """
    # Build Researcher Subgraph
    researcher_builder = StateGraph(ResearcherState)
    researcher_builder.add_node("generate_queries", generate_queries_node)
    researcher_builder.add_node("perform_search", perform_search_node)
    researcher_builder.add_node("synthesize_research", synthesize_research_node)
    
    researcher_builder.add_edge(START, "generate_queries")
    researcher_builder.add_conditional_edges("generate_queries", map_queries, ["perform_search"])
    researcher_builder.add_edge("perform_search", "synthesize_research")
    researcher_builder.add_edge("synthesize_research", END)
    
    return researcher_builder.compile()


# Compile the subgraph at module level
researcher_graph = build_researcher_subgraph()

