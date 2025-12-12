"""
Process and rank markets node for the market research subgraph.

Processes raw events and ranks them for relevance.
"""
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage

from polyplexity_agent.config import Settings
from polyplexity_agent.streaming.event_serializers import create_trace_event
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.prompts.market_prompts import MARKET_RANKING_PROMPT
from polyplexity_agent.utils.helpers import create_llm_model, log_node_state

# Application settings
settings = Settings()
logger = get_logger(__name__)


def _rank_markets_llm(original_topic: str, markets: List[Dict]) -> Dict[str, Any]:
    """Rank markets using an LLM."""
    model = create_llm_model().with_structured_output(Dict[str, Any])
    prompt = MARKET_RANKING_PROMPT.format(original_topic=original_topic, candidate_markets=markets)
    return model.invoke([HumanMessage(content=prompt)])


def process_and_rank_markets_node(state: MarketResearchState):
    """Process raw events and rank them for relevance."""
    try:
        # Access state logger from market_research module temporarily (like Phase 5 pattern)
        from polyplexity_agent.graphs.subgraphs.market_research import _state_logger
        log_node_state(_state_logger, "process_and_rank_markets", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Raw events: {len(state.get('raw_events', []))}")
        
        original_topic = state["original_topic"]
        events = state["raw_events"][:5]  # Limit to 5 events for now
        
        # In a real scenario, you might fetch full details here. For now, we use the search results.
        ranked_markets_response = _rank_markets_llm(original_topic, events)
        ranked_markets = ranked_markets_response.get("ranked_markets", [])
        
        node_call_event = create_trace_event("node_call", "process_and_rank_markets", {"ranked_count": len(ranked_markets)})
        stream_trace_event("node_call", "process_and_rank_markets", {"ranked_count": len(ranked_markets)})
        
        result = {"candidate_markets": ranked_markets, "reasoning_trace": ["Ranked candidate markets."], "execution_trace": [node_call_event]}
        log_node_state(_state_logger, "process_and_rank_markets", "SUBGRAPH", {**state, **result}, "AFTER", additional_info=f"Ranked {len(ranked_markets)} markets")
        return result
    except Exception as e:
        stream_custom_event("error", "process_and_rank_markets", {"error": str(e)})
        logger.error("process_and_rank_markets_node_error", error=str(e), exc_info=True)
        raise
