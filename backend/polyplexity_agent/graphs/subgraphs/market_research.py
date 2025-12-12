"""
Market research subgraph implementation.

Handles market research workflow: Topic -> Generate Queries -> Fetch Markets -> Process & Rank -> Evaluate
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


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


def build_market_research_subgraph():
    """Build and compile the market research subgraph."""
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
    """Create the market research subgraph (alias for build_market_research_subgraph)."""
    return build_market_research_subgraph()


# Compile the subgraph at module level
market_research_graph = build_market_research_subgraph()
