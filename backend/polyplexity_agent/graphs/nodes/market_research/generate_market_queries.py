"""
Generate market queries node for the market research subgraph.

Generates search queries for Polymarket based on the original research topic.
"""
from typing import Dict, List
from langchain_core.messages import HumanMessage

from polyplexity_agent.config import Settings
from polyplexity_agent.streaming.event_serializers import create_trace_event
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.prompts.market_prompts import MARKET_QUERY_GENERATION_PROMPT
from polyplexity_agent.utils.helpers import create_llm_model, log_node_state

# Application settings
settings = Settings()
logger = get_logger(__name__)


def _generate_market_queries_llm(original_topic: str) -> Dict[str, List[str]]:
    """Generate search queries for Polymarket using an LLM."""
    model = create_llm_model().with_structured_output(Dict[str, List[str]])
    prompt = MARKET_QUERY_GENERATION_PROMPT.format(original_topic=original_topic)
    return model.invoke([HumanMessage(content=prompt)])


def generate_market_queries_node(state: MarketResearchState):
    """Generate keywords for Polymarket search based on the original topic."""
    try:
        # Access state logger from market_research module temporarily (like Phase 5 pattern)
        from polyplexity_agent.graphs.subgraphs.market_research import _state_logger
        log_node_state(_state_logger, "generate_market_queries", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Topic: {state.get('original_topic', 'N/A')}")
        
        original_topic = state["original_topic"]
        response = _generate_market_queries_llm(original_topic)
        queries = response.get("queries", [])
        
        node_call_event = create_trace_event("node_call", "generate_market_queries", {})
        queries_event = create_trace_event("custom", "generate_market_queries", {"event": "generated_market_queries", "queries": queries})
        
        stream_trace_event("node_call", "generate_market_queries", {})
        stream_trace_event("custom", "generate_market_queries", {"event": "generated_market_queries", "queries": queries})
        stream_custom_event("generated_market_queries", "generate_market_queries", {"queries": queries})
        
        result = {"market_queries": queries, "reasoning_trace": ["Generated market queries."], "execution_trace": [node_call_event, queries_event]}
        log_node_state(_state_logger, "generate_market_queries", "SUBGRAPH", {**state, **result}, "AFTER", additional_info=f"Generated {len(queries)} queries")
        return result
    except Exception as e:
        stream_custom_event("error", "generate_market_queries", {"error": str(e)})
        logger.error("generate_market_queries_node_error", error=str(e), exc_info=True)
        raise
