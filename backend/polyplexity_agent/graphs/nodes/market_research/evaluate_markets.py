"""
Evaluate markets node for the market research subgraph.

Evaluates the ranked markets to ensure they are high quality.
"""
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage

from polyplexity_agent.config import Settings
from polyplexity_agent.streaming.event_serializers import create_trace_event
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.prompts.market_prompts import MARKET_EVALUATION_PROMPT
from polyplexity_agent.utils.helpers import create_llm_model, log_node_state

# Application settings
settings = Settings()
logger = get_logger(__name__)


def _evaluate_markets_llm(original_topic: str, ranked_markets: List[Dict]) -> Dict[str, Any]:
    """Evaluate ranked markets using an LLM."""
    model = create_llm_model().with_structured_output(Dict[str, Any])
    prompt = MARKET_EVALUATION_PROMPT.format(original_topic=original_topic, ranked_markets=ranked_markets)
    return model.invoke([HumanMessage(content=prompt)])


def evaluate_markets_node(state: MarketResearchState):
    """Evaluate the ranked markets to ensure they are high quality."""
    try:
        # Access state logger from market_research module temporarily (like Phase 5 pattern)
        from polyplexity_agent.graphs.subgraphs.market_research import _state_logger
        log_node_state(_state_logger, "evaluate_markets", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Candidate markets: {len(state.get('candidate_markets', []))}")
        
        original_topic = state["original_topic"]
        candidate_markets = state["candidate_markets"]
        
        evaluation = _evaluate_markets_llm(original_topic, candidate_markets)
        decision = evaluation.get("decision", "REJECT")  # Default to reject
        final_markets = evaluation.get("markets", [])
        
        if decision.upper() == "APPROVE":
            approved_markets = final_markets
        else:
            approved_markets = []  # Or you could use the refined list
        
        node_call_event = create_trace_event("node_call", "evaluate_markets", {"decision": decision, "approved_count": len(approved_markets)})
        stream_trace_event("node_call", "evaluate_markets", {"decision": decision, "approved_count": len(approved_markets)})
        
        result = {"approved_markets": approved_markets, "reasoning_trace": [f"Evaluation result: {decision}"], "execution_trace": [node_call_event]}
        log_node_state(_state_logger, "evaluate_markets", "SUBGRAPH", {**state, **result}, "AFTER", additional_info=f"Decision: {decision}, Approved: {len(approved_markets)}")
        return result
    except Exception as e:
        stream_custom_event("error", "evaluate_markets", {"error": str(e)})
        logger.error("evaluate_markets_node_error", error=str(e), exc_info=True)
        raise
