"""
Fetch markets node for the market research subgraph.

Fetches market data from Polymarket by querying events filtered by tag IDs.
Retrieves events for each tag ID, extracts markets from events, and
deduplicates markets by slug before returning them.
"""
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.streaming import stream_custom_event
from polyplexity_agent.tools.polymarket import fetch_events_by_tag_id

logger = get_logger(__name__)


def fetch_markets_node(state: MarketResearchState):
    """
    Fetch market data from Polymarket based on tag IDs.

    Iterates through tag IDs in the state, fetches events for each tag,
    extracts markets from events, and deduplicates by market slug.

    Args:
        state: The market research state containing market_queries (tag IDs).

    Returns:
        A dictionary containing:
            - raw_events: List of unique market dictionaries (deduplicated)
            - reasoning_trace: List with a summary message

    Raises:
        Exception: If fetching fails, streams an error event and re-raises.
    """
    try:
        tag_ids = state["market_queries"]
        all_events = []

        for tag_id in tag_ids:
            all_events.extend(fetch_events_by_tag_id(tag_id))

        # Flatten markets from events into a single list
        all_markets = []
        for event in all_events:
            markets = event.get("markets", [])
            all_markets.extend(markets)

        # Deduplicate by market slug
        seen_slugs = set()
        unique_markets = []
        for market in all_markets:
            market_slug = market.get("slug", "")
            if market_slug and market_slug not in seen_slugs:
                unique_markets.append(market)
                seen_slugs.add(market_slug)

        return {
            "raw_events": unique_markets,
            "reasoning_trace": ["Fetched and deduplicated markets."],
        }
    except Exception as e:
        stream_custom_event("error", "fetch_markets", {"error": str(e)})
        logger.error("fetch_markets_node_error", error=str(e), exc_info=True)
        raise
