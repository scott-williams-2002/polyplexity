"""
Generate queries node for the researcher subgraph.

Breaks a research topic into distinct search queries using LLM.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from polyplexity_agent.config import Settings
from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.graphs.state import ResearcherState
from polyplexity_agent.models import SearchQueries
from polyplexity_agent.prompts.researcher import (
    QUERY_GENERATION_SYSTEM_PROMPT,
    QUERY_GENERATION_USER_PROMPT_TEMPLATE,
)
from polyplexity_agent.utils.helpers import create_llm_model, format_date, log_node_state

# Application settings
settings = Settings()


def _generate_queries_llm(state: ResearcherState) -> SearchQueries:
    """Generate search queries using LLM."""
    model = create_llm_model().with_structured_output(SearchQueries).with_retry(stop_after_attempt=settings.max_structured_output_retries)
    system_prompt = QUERY_GENERATION_SYSTEM_PROMPT
    user_prompt = QUERY_GENERATION_USER_PROMPT_TEMPLATE.format(
        current_date=format_date(),
        topic=state['topic']
    )
    return model.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])


def generate_queries_node(state: ResearcherState):
    """Breaks a research topic into distinct search queries."""
    try:
        # Access state logger from researcher module temporarily (like Phase 4 pattern)
        from polyplexity_agent.graphs.subgraphs.researcher import _state_logger
        log_node_state(_state_logger, "generate_queries", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Topic: {state.get('topic', 'N/A')}")
        writer = get_stream_writer()
        writer({"event": "researcher_thinking", "topic": state['topic']})
        
        resp = _generate_queries_llm(state)
        node_call_event = create_trace_event("node_call", "generate_queries", {})
        queries_event = create_trace_event("custom", "generate_queries", {"event": "generated_queries", "queries": resp.queries})
        
        writer({"event": "trace", **node_call_event})
        writer({"event": "trace", **queries_event})
        writer({"event": "generated_queries", "queries": resp.queries})
        
        log_node_state(_state_logger, "generate_queries", "SUBGRAPH", {**state, "queries": resp.queries}, "AFTER", additional_info=f"Generated {len(resp.queries)} queries")
        return {"queries": resp.queries, "execution_trace": [node_call_event, queries_event]}
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "generate_queries", "error": str(e)})
        print(f"Error in generate_queries_node: {e}")
        raise
