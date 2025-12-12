"""
Evaluate markets node for the market research subgraph.

Evaluates ranked markets using LLM-based evaluation, streams approved
markets incrementally as they're evaluated, and streams a final reasoning
summary. Includes fallback logic to use top markets if LLM returns no
approved markets.
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from polyplexity_agent.config import Settings
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.models import ApprovedMarkets
from polyplexity_agent.prompts.market_prompts import MARKET_EVALUATION_PROMPT
from polyplexity_agent.streaming import stream_custom_event
from polyplexity_agent.utils.helpers import create_llm_model

# Application settings
settings = Settings()
logger = get_logger(__name__)


def _evaluate_markets_llm(
    original_topic: str, market_info: List[Dict[str, Any]]
) -> ApprovedMarkets:
    """
    Evaluate ranked markets using an LLM, returning only slugs and reasoning.

    Uses an LLM with structured output to evaluate markets and determine
    which ones should be approved based on relevance and quality.

    Args:
        original_topic: The user's original research topic.
        market_info: List of dictionaries containing slug, name, and
            clobTokenIds for each market.

    Returns:
        An ApprovedMarkets object containing approved slugs and reasoning.
    """
    model = (
        create_llm_model()
        .with_structured_output(ApprovedMarkets)
        .with_retry(stop_after_attempt=settings.max_structured_output_retries)
    )
    markets_str = "\n".join(
        [
            f"- Slug: {m['slug']}, Name: {m['name']}, clobTokenIds: {m.get('clobTokenIds', [])}"
            for m in market_info
        ]
    )
    prompt = MARKET_EVALUATION_PROMPT.format(
        original_topic=original_topic, ranked_markets=markets_str
    )
    return model.invoke([HumanMessage(content=prompt)])


def evaluate_markets_node(state: MarketResearchState):
    """
    Evaluate ranked markets and stream markets incrementally, then final reasoning.

    Evaluates candidate markets using LLM, streams each approved market
    incrementally as a market_approved event, and streams a final
    market_research_complete event with reasoning. Includes fallback logic
    to use top markets if evaluation returns no results.

    Args:
        state: The market research state containing original_topic,
            candidate_markets, and reasoning_trace.

    Returns:
        A dictionary containing:
            - approved_markets: List of approved market dictionaries
            - reasoning_trace: List with evaluation reasoning

    Raises:
        Exception: If evaluation fails, streams an error event and re-raises.
    """
    try:
        original_topic = state["original_topic"]
        candidate_markets = state["candidate_markets"]

        # Fallback: If candidate_markets is empty, use raw_events directly
        if not candidate_markets:
            logger.warning("No candidate markets available, using raw markets directly")
            raw_events = state.get("raw_events", [])
            fallback_count = min(10, len(raw_events))
            candidate_markets = raw_events[:fallback_count]

        # Extract slugs, names, and clobTokenIds for LLM
        market_info = []
        for market in candidate_markets:
            slug = market.get("slug", "")
            question = market.get("question", "")
            clob_token_ids = market.get("clobTokenIds", [])
            name = question[:60].split("?")[0] if question else slug
            market_info.append({"slug": slug, "name": name, "clobTokenIds": clob_token_ids})

        # Get approved slugs + reasoning from LLM
        evaluation = _evaluate_markets_llm(original_topic, market_info)
        approved_slugs = evaluation.slugs
        reasoning = evaluation.reasoning

        # Create lookup dictionary for full market data
        market_lookup = {market.get("slug", ""): market for market in candidate_markets}

        # Collect approved markets and stream each incrementally
        approved_markets = []
        for slug in approved_slugs:
            if slug in market_lookup:
                market = market_lookup[slug]
                approved_markets.append(market)
                # Stream each approved market incrementally
                stream_custom_event(
                    "market_approved",
                    "evaluate_markets",
                    {
                        "slug": market.get("slug", ""),
                        "clobTokenIds": market.get("clobTokenIds", []),
                        "question": market.get("question", ""),
                        "description": market.get("description", ""),
                        "rules": market.get("description", ""),
                    },
                )

        # Fallback: If LLM returned no approved markets, use top markets
        if not approved_markets:
            logger.warning("LLM returned empty approved markets list, using fallback")
            fallback_count = min(5, len(candidate_markets))
            approved_markets = candidate_markets[:fallback_count]
            reasoning = f"No markets approved by LLM, using top {fallback_count} ranked markets as fallback"
            # Stream fallback markets incrementally
            for market in approved_markets:
                stream_custom_event(
                    "market_approved",
                    "evaluate_markets",
                    {
                        "slug": market.get("slug", ""),
                        "clobTokenIds": market.get("clobTokenIds", []),
                        "question": market.get("question", ""),
                        "description": market.get("description", ""),
                        "rules": market.get("description", ""),
                    },
                )

        # Stream final event with reasoning only (markets already streamed incrementally)
        reasoning_trace = state.get("reasoning_trace", [])
        all_reasoning = "\n".join(reasoning_trace + [reasoning]) if reasoning_trace else reasoning

        stream_custom_event(
            "market_research_complete",
            "evaluate_markets",
            {"reasoning": all_reasoning},
        )

        return {
            "approved_markets": approved_markets,
            "reasoning_trace": [reasoning],
        }
    except Exception as e:
        stream_custom_event("error", "evaluate_markets", {"error": str(e)})
        logger.error("evaluate_markets_node_error", error=str(e), exc_info=True)
        raise
