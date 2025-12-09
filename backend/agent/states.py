"""
State definitions for the research agent graph system.
Uses TypedDict for type safety and Annotated reducers for state accumulation.
"""
import operator
from typing import Annotated, List, Optional, TypedDict


class ResearcherState(TypedDict):
    """
    State schema for the researcher subgraph.
    
    This subgraph handles the research workflow:
    Topic -> Generate Queries -> Parallel Search -> Synthesize Results
    
    Fields:
        topic: The research topic to investigate
        queries: List of search queries generated from the topic
        search_results: Accumulated search results from parallel searches (uses operator.add)
        research_summary: Final synthesized summary of all research
        query_breadth: Maximum number of results per Tavily search (3-5)
    """
    topic: str
    queries: List[str]
    search_results: Annotated[List[str], operator.add]  # Accumulates search results
    research_summary: str
    query_breadth: int


class SupervisorState(TypedDict, total=False):
    """
    State schema for the main supervisor graph.
    
    This graph orchestrates the research workflow:
    Assess -> Delegate to Researcher -> Assess -> Write Report
    
    Fields:
        user_request: The original user question/request
        research_notes: Accumulated research notes from multiple iterations (uses operator.add)
        next_topic: The next topic to research (or "FINISH" to end)
        final_report: The final generated report
        iterations: Current iteration count (prevents infinite loops)
        conversation_history: Accumulated conversation history as structured messages (uses operator.add)
        current_report_version: Version number for report refinement in follow-ups
        execution_trace: Accumulated execution trace events for current question only (uses operator.add)
        research_iterations: Number of research loops to perform (-1, 0, 1-3)
        query_breadth: Maximum number of results per Tavily search (3-5)
        _thread_id: Internal field for passing thread_id to nodes (not persisted in checkpoints)
        _question_execution_trace: Internal field for passing current question's execution trace to final_report_node (not persisted in checkpoints)
    """
    user_request: str
    research_notes: Annotated[List[str], operator.add]  # Accumulates notes from iterations
    next_topic: str  # To pass to subgraph
    final_report: str
    iterations: int
    conversation_history: Annotated[List[dict], operator.add]  # Structured messages: [{"role": "user"|"assistant", "content": str, "execution_trace": List[dict]|None}, ...]
    current_report_version: int  # Track report iterations for refinement
    execution_trace: Annotated[List[dict], operator.add]  # Track execution trace events (reset per question)
    research_iterations: int  # -1 (Clarify), 0 (Direct), 1-3 (Research)
    query_breadth: int  # Tavily search depth (3-5)
    _thread_id: Optional[str]  # Internal: thread_id for storing messages in separate table
    _question_execution_trace: Optional[List[dict]]  # Internal: current question's execution trace for final_report_node

