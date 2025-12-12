from langgraph.graph import StateGraph, END, START
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.market_nodes import (
    generate_market_queries_node,
    fetch_markets_node,
    process_and_rank_markets_node,
    evaluate_markets_node,
)

def build_market_subgraph():
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

market_research_graph = build_market_subgraph()
