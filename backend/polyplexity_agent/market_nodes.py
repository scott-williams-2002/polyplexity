from typing import List, Dict, Any
from langgraph.config import get_stream_writer
from langchain_core.messages import HumanMessage

from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.tools.polymarket import search_markets, get_event_details
from polyplexity_agent.prompts.market_prompts import (
    MARKET_QUERY_GENERATION_PROMPT,
    MARKET_RANKING_PROMPT,
    MARKET_EVALUATION_PROMPT,
)
from polyplexity_agent.utils.helpers import create_llm_model, log_node_state

def _generate_market_queries_llm(original_topic: str) -> Dict[str, List[str]]:
    """Generate search queries for Polymarket using an LLM."""
    model = create_llm_model().with_structured_output(Dict[str, List[str]])
    prompt = MARKET_QUERY_GENERATION_PROMPT.format(original_topic=original_topic)
    return model.invoke([HumanMessage(content=prompt)])

def generate_market_queries_node(state: MarketResearchState):
    """Generate keywords for Polymarket search based on the original topic."""
    original_topic = state["original_topic"]
    response = _generate_market_queries_llm(original_topic)
    queries = response.get("queries", [])
    return {"market_queries": queries, "reasoning_trace": ["Generated market queries."]}

def fetch_markets_node(state: MarketResearchState):
    """Fetch market data from Polymarket based on generated queries."""
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
            
    return {"raw_events": unique_events, "reasoning_trace": ["Fetched and deduplicated raw events."]}

def _rank_markets_llm(original_topic: str, markets: List[Dict]) -> Dict[str, Any]:
    """Rank markets using an LLM."""
    model = create_llm_model().with_structured_output(Dict[str, Any])
    prompt = MARKET_RANKING_PROMPT.format(original_topic=original_topic, candidate_markets=markets)
    return model.invoke([HumanMessage(content=prompt)])

def process_and_rank_markets_node(state: MarketResearchState):
    """Process raw events and rank them for relevance."""
    original_topic = state["original_topic"]
    events = state["raw_events"][:5]  # Limit to 5 events for now
    
    # In a real scenario, you might fetch full details here. For now, we use the search results.
    ranked_markets_response = _rank_markets_llm(original_topic, events)
    ranked_markets = ranked_markets_response.get("ranked_markets", [])
    
    return {"candidate_markets": ranked_markets, "reasoning_trace": ["Ranked candidate markets."]}

def _evaluate_markets_llm(original_topic: str, ranked_markets: List[Dict]) -> Dict[str, Any]:
    """Evaluate ranked markets using an LLM."""
    model = create_llm_model().with_structured_output(Dict[str, Any])
    prompt = MARKET_EVALUATION_PROMPT.format(original_topic=original_topic, ranked_markets=ranked_markets)
    return model.invoke([HumanMessage(content=prompt)])

def evaluate_markets_node(state: MarketResearchState):
    """Evaluate the ranked markets to ensure they are high quality."""
    original_topic = state["original_topic"]
    candidate_markets = state["candidate_markets"]
    
    evaluation = _evaluate_markets_llm(original_topic, candidate_markets)
    decision = evaluation.get("decision", "REJECT") # Default to reject
    final_markets = evaluation.get("markets", [])
    
    if decision.upper() == "APPROVE":
        approved_markets = final_markets
    else:
        approved_markets = [] # Or you could use the refined list

    return {"approved_markets": approved_markets, "reasoning_trace": [f"Evaluation result: {decision}"]}
