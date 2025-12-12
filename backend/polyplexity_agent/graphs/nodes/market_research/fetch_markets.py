"""
Fetch markets node for the market research subgraph.

Fetches market data from Polymarket based on generated queries.
"""
from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.tools.polymarket import search_markets
from polyplexity_agent.utils.helpers import log_node_state


def fetch_markets_node(state: MarketResearchState):
    """Fetch market data from Polymarket based on generated queries."""
    try:
        # Access state logger from market_research module temporarily (like Phase 5 pattern)
        from polyplexity_agent.graphs.subgraphs.market_research import _state_logger
        log_node_state(_state_logger, "fetch_markets", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Queries: {len(state.get('market_queries', []))}")
        
        queries = state["market_queries"]
        all_events = []
        for query in queries:
            all_events.extend(search_markets(query))
        
        # Simple deduplication
        seen_slugs = set()
        unique_events = []
        for event in all_events:
            if event["slug"] not in seen_slugs:
                unique_events.append(event)
                seen_slugs.add(event["slug"])
        
        node_call_event = create_trace_event("node_call", "fetch_markets", {"events_found": len(unique_events)})
        stream_trace_event("node_call", "fetch_markets", {"events_found": len(unique_events)})
        
        result = {"raw_events": unique_events, "reasoning_trace": ["Fetched and deduplicated raw events."], "execution_trace": [node_call_event]}
        log_node_state(_state_logger, "fetch_markets", "SUBGRAPH", {**state, **result}, "AFTER", additional_info=f"Fetched {len(unique_events)} unique events")
        return result
    except Exception as e:
        stream_custom_event("error", "fetch_markets", {"error": str(e)})
        print(f"Error in fetch_markets_node: {e}")
        raise
