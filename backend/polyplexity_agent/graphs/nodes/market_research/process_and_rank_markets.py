"""
Process and rank markets node for the market research subgraph.

Processes raw markets and ranks them for relevance to the research topic
using LLM-based ranking. Limits to top 20 markets for ranking efficiency
and includes fallback logic if LLM returns no results.
"""
from typing import Dict, List

from langchain_core.messages import HumanMessage

from polyplexity_agent.config import Settings
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.models import RankedMarkets
from polyplexity_agent.prompts.market_prompts import MARKET_RANKING_PROMPT
from polyplexity_agent.streaming import stream_custom_event
from polyplexity_agent.utils.helpers import create_llm_model

# Application settings
settings = Settings()
logger = get_logger(__name__)


def _rank_markets_llm(
    original_topic: str, market_slugs_and_names: List[Dict[str, str]]
) -> RankedMarkets:
    """
    Rank markets using an LLM, returning only slugs and reasoning.

    Uses an LLM with structured output to rank markets by relevance to
    the original topic, returning ranked slugs and reasoning.

    Args:
        original_topic: The user's original research topic.
        market_slugs_and_names: List of dictionaries containing slug and
            name fields for each market.

    Returns:
        A RankedMarkets object containing ranked slugs and reasoning.
    """
    model = (
        create_llm_model()
        .with_structured_output(RankedMarkets)
        .with_retry(stop_after_attempt=settings.max_structured_output_retries)
    )
    markets_str = "\n".join(
        [f"- Slug: {m['slug']}, Name: {m['name']}" for m in market_slugs_and_names]
    )
    prompt = MARKET_RANKING_PROMPT.format(
        original_topic=original_topic, candidate_markets=markets_str
    )
    return model.invoke([HumanMessage(content=prompt)])


def process_and_rank_markets_node(state: MarketResearchState):
    """
    Process raw markets and rank them for relevance.

    Extracts market slugs and names, uses LLM to rank them by relevance,
    and reconstructs full market data from ranked slugs. Includes fallback
    logic to use top markets if LLM returns no results.

    Args:
        state: The market research state containing original_topic and
            raw_events (markets).

    Returns:
        A dictionary containing:
            - candidate_markets: List of ranked market dictionaries
            - reasoning_trace: List with ranking reasoning

    Raises:
        Exception: If ranking fails, streams an error event and re-raises.
    """
    try:
        original_topic = state["original_topic"]
        raw_markets = state["raw_events"][:20]  # Limit to 20 markets for ranking

        # Extract slugs and shortened names for LLM
        market_slugs_and_names = []
        for market in raw_markets:
            slug = market.get("slug", "")
            question = market.get("question", "")
            name = question[:60].split("?")[0] if question else slug
            market_slugs_and_names.append({"slug": slug, "name": name})

        # Get ranked slugs + reasoning from LLM
        ranked_response = _rank_markets_llm(original_topic, market_slugs_and_names)
        ranked_slugs = ranked_response.slugs
        reasoning = ranked_response.reasoning

        # Create lookup dictionary for full market data
        market_lookup = {market.get("slug", ""): market for market in raw_markets}

        # Piece together full market data from slugs
        ranked_markets = []
        for slug in ranked_slugs:
            if slug in market_lookup:
                ranked_markets.append(market_lookup[slug])

        # Fallback: If LLM returned no markets, use top markets as fallback
        if not ranked_markets:
            logger.warning("LLM returned empty ranked markets list, using fallback")
            fallback_count = min(10, len(raw_markets))
            ranked_markets = raw_markets[:fallback_count]
            reasoning = f"No markets ranked by LLM, using top {fallback_count} markets as fallback"

        return {
            "candidate_markets": ranked_markets,
            "reasoning_trace": [f"Ranked markets: {reasoning}"],
        }
    except Exception as e:
        stream_custom_event("error", "process_and_rank_markets", {"error": str(e)})
        logger.error("process_and_rank_markets_node_error", error=str(e), exc_info=True)
        raise
