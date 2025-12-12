"""
Market research subgraph implementation.

Handles market research workflow using tag-based selection:
1. Generate Market Queries: Selects relevant tags from Polymarket in batches
2. Fetch Markets: Retrieves events and markets filtered by selected tag IDs
3. Process & Rank: Ranks markets by relevance to the research topic
4. Evaluate: Evaluates and approves markets, streaming results incrementally

The subgraph streams incremental events for tags and markets, then provides
a final reasoning summary.
"""
from typing import Optional

from langgraph.graph import END, START, StateGraph

from polyplexity_agent.graphs.nodes.market_research import (
    evaluate_markets_node,
    fetch_markets_node,
    generate_market_queries_node,
    process_and_rank_markets_node,
)
from polyplexity_agent.graphs.state import MarketResearchState

# Global state logger instance (temporary, like Phase 5 pattern)
_state_logger: Optional[object] = None


def set_state_logger(logger: object) -> None:
    """
    Set the global state logger instance.

    This function is used to configure a logger for state tracking within
    the market research subgraph. The logger is stored globally to allow
    access from node functions without circular import issues.

    Args:
        logger: The logger instance to use for state logging.
    """
    global _state_logger
    _state_logger = logger


def build_market_research_subgraph():
    """
    Build and compile the market research subgraph.

    Constructs a LangGraph StateGraph with the following workflow:
    - generate_market_queries: Selects relevant tags from Polymarket
    - fetch_markets: Fetches events and markets by tag IDs
    - process_and_rank_markets: Ranks markets by relevance
    - evaluate_markets: Evaluates and approves markets

    Returns:
        A compiled LangGraph StateGraph ready for execution.
    """
    builder = StateGraph(MarketResearchState)
    builder.add_node("generate_market_queries", generate_market_queries_node)
    builder.add_node("fetch_markets", fetch_markets_node)
    builder.add_node("process_and_rank_markets", process_and_rank_markets_node)
    builder.add_node("evaluate_markets", evaluate_markets_node)

    builder.add_edge(START, "generate_market_queries")
    builder.add_edge("generate_market_queries", "fetch_markets")
    builder.add_edge("fetch_markets", "process_and_rank_markets")
    builder.add_edge("process_and_rank_markets", "evaluate_markets")
    builder.add_edge("evaluate_markets", END)

    return builder.compile()


def create_market_research_graph():
    """
    Create the market research subgraph.

    This is an alias for build_market_research_subgraph() provided for
    consistency with other subgraph creation functions.

    Returns:
        A compiled LangGraph StateGraph ready for execution.
    """
    return build_market_research_subgraph()


# Compile the subgraph at module level
market_research_graph = build_market_research_subgraph()
