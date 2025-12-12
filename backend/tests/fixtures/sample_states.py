"""
Factory functions for creating sample state dictionaries.

Provides helper functions to create states with specific configurations
for testing different scenarios.
"""
from typing import Any, Dict, List, Optional

from polyplexity_agent.graphs.state import (
    MarketResearchState,
    ResearcherState,
    SupervisorState,
)


def create_supervisor_state(
    user_request: str = "What is the weather?",
    research_notes: Optional[List[str]] = None,
    iterations: int = 0,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    conversation_summary: str = "",
    current_report_version: int = 0,
    next_topic: str = "",
    final_report: str = "",
    execution_trace: Optional[List[Dict[str, Any]]] = None,
    answer_format: str = "concise",
    thread_id: Optional[str] = None,
) -> SupervisorState:
    """Create SupervisorState with specified configuration.

    Args:
        user_request: The user's question or request.
        research_notes: List of research notes accumulated.
        iterations: Current iteration count.
        conversation_history: List of conversation messages.
        conversation_summary: Summarized conversation context.
        current_report_version: Version number for report refinement.
        next_topic: Next topic to research or "FINISH".
        final_report: Generated final report.
        execution_trace: List of execution trace events.
        answer_format: "concise" or "report".
        thread_id: Optional thread ID for checkpointing.

    Returns:
        SupervisorState dictionary.
    """
    state: SupervisorState = {
        "user_request": user_request,
        "research_notes": research_notes or [],
        "iterations": iterations,
        "conversation_history": conversation_history or [],
        "conversation_summary": conversation_summary,
        "current_report_version": current_report_version,
        "next_topic": next_topic,
        "final_report": final_report,
        "execution_trace": execution_trace or [],
        "answer_format": answer_format,
    }
    if thread_id:
        state["_thread_id"] = thread_id
    return state


def create_researcher_state(
    topic: str = "artificial intelligence",
    queries: Optional[List[str]] = None,
    search_results: Optional[List[str]] = None,
    research_summary: str = "",
    query_breadth: int = 3,
) -> ResearcherState:
    """Create ResearcherState with specified configuration.

    Args:
        topic: Research topic to investigate.
        queries: List of generated search queries.
        search_results: Accumulated search results.
        research_summary: Final synthesized summary.
        query_breadth: Maximum results per Tavily search.

    Returns:
        ResearcherState dictionary.
    """
    return {
        "topic": topic,
        "queries": queries or [],
        "search_results": search_results or [],
        "research_summary": research_summary,
        "query_breadth": query_breadth,
    }


def create_market_research_state(
    original_topic: str = "2024 US presidential election",
    market_queries: Optional[List[str]] = None,
    raw_events: Optional[List[Dict[str, Any]]] = None,
    candidate_markets: Optional[List[Dict[str, Any]]] = None,
    approved_markets: Optional[List[Dict[str, Any]]] = None,
    reasoning_trace: Optional[List[str]] = None,
) -> MarketResearchState:
    """Create MarketResearchState with specified configuration.

    Args:
        original_topic: User's original research topic.
        market_queries: Generated Polymarket search queries.
        raw_events: Unprocessed event data from API.
        candidate_markets: Processed markets for ranking.
        approved_markets: Final approved markets.
        reasoning_trace: Accumulated reasoning steps.

    Returns:
        MarketResearchState dictionary.
    """
    return {
        "original_topic": original_topic,
        "market_queries": market_queries or [],
        "raw_events": raw_events or [],
        "candidate_markets": candidate_markets or [],
        "approved_markets": approved_markets or [],
        "reasoning_trace": reasoning_trace or [],
    }


def create_empty_supervisor_state() -> SupervisorState:
    """Create empty SupervisorState for edge case testing.

    Returns:
        Empty SupervisorState dictionary.
    """
    return create_supervisor_state(
        user_request="",
        research_notes=[],
        iterations=0,
    )


def create_max_iterations_supervisor_state() -> SupervisorState:
    """Create SupervisorState at max iterations limit.

    Returns:
        SupervisorState with iterations=10.
    """
    return create_supervisor_state(iterations=10)


def create_follow_up_supervisor_state() -> SupervisorState:
    """Create SupervisorState for follow-up conversation.

    Returns:
        SupervisorState with existing conversation context.
    """
    return create_supervisor_state(
        user_request="Tell me more",
        conversation_history=[
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is..."},
        ],
        conversation_summary="Previous conversation about AI",
        current_report_version=1,
    )


def create_researcher_state_with_results() -> ResearcherState:
    """Create ResearcherState with search results populated.

    Returns:
        ResearcherState with search results.
    """
    return create_researcher_state(
        topic="artificial intelligence",
        queries=["AI definition", "AI applications"],
        search_results=["Result 1", "Result 2"],
        research_summary="AI is a branch of computer science...",
    )
