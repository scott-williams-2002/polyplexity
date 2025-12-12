"""
State definitions for the research agent graph system.
Uses TypedDict for type safety and Annotated reducers for state accumulation.
"""
import operator
from typing import Annotated, Dict, List, Optional, TypedDict

# Import manage_chat_history - this creates a circular dependency that is resolved
# by importing state classes before importing supervisor nodes in __init__.py
from polyplexity_agent.graphs.nodes.supervisor.summarize_conversation import manage_chat_history


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


class MarketResearchState(TypedDict, total=False):
    """
    State schema for the market research subgraph.

    Fields:
        original_topic: The user's original research topic
        ai_response: Optional AI-generated report/response providing context for tag selection
        market_queries: Tag IDs or keywords generated for Polymarket search
        raw_events: Unprocessed event data from API
        candidate_markets: Processed and filtered markets for LLM ranking
        approved_markets: Final list of markets approved by evaluation
        reasoning_trace: Accumulated reasoning steps from the subgraph
        tangential_iteration: Current retry attempt count (0-3)
        previous_queries: Previously attempted queries for context
    """
    original_topic: str
    ai_response: Optional[str]
    market_queries: List[str]
    raw_events: List[Dict]
    candidate_markets: List[Dict]
    approved_markets: List[Dict]
    reasoning_trace: Annotated[List[str], operator.add]
    tangential_iteration: int
    previous_queries: List[str]


class SupervisorState(TypedDict, total=False):
    """
    State schema for the main supervisor graph.
    
    This graph orchestrates the research workflow:
    Assess -> Delegate to Researcher -> Assess -> Write Report
    
    Fields:
        user_request: The original user question/request
        research_notes: Accumulated research notes from multiple iterations (uses operator.add)
        prediction_markets: List of approved prediction markets to include in the report
        next_topic: The next topic to research (or "FINISH" to end)
        final_report: The final generated report
        iterations: Current iteration count (prevents infinite loops)
        conversation_history: Accumulated conversation history as structured messages (uses operator.add)
        current_report_version: Version number for report refinement in follow-ups
        execution_trace: Accumulated execution trace events for current question only (uses operator.add)
        answer_format: "concise" or "report"
        approved_markets: List of approved markets returned from market research subgraph
        polymarket_blurb: Optional rewritten convincing market recommendation text
        _thread_id: Internal field for passing thread_id to nodes (not persisted in checkpoints)
        _question_execution_trace: Internal field for passing current question's execution trace to final_report_node (not persisted in checkpoints)
    """
    user_request: str
    research_notes: Annotated[List[str], operator.add]  # Accumulates notes from iterations
    prediction_markets: List[Dict]  # Approved prediction markets
    next_topic: str  # To pass to subgraph
    final_report: str
    iterations: int
    conversation_summary: str  # Summarized context
    conversation_history: Annotated[List[dict], manage_chat_history]  # Structured messages: [{"role": "user"|"assistant", "content": str, "execution_trace": List[dict]|None}, ...]
    current_report_version: int  # Track report iterations for refinement
    execution_trace: Annotated[List[dict], operator.add]  # Track execution trace events (reset per question)
    answer_format: str  # "concise" or "report"
    approved_markets: List[Dict]  # Approved markets from market research subgraph
    polymarket_blurb: Optional[str]  # Rewritten convincing market recommendation text
    _thread_id: Optional[str]  # Internal: thread_id for storing messages in separate table
    _question_execution_trace: Optional[List[dict]]  # Internal: current question's execution trace for final_report_node

