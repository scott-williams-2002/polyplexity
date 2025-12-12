"""
Synthesize research node for the researcher subgraph.

Summarizes all search results into a clean research note.
"""
from langchain_core.messages import HumanMessage

from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.graphs.state import ResearcherState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.prompts.researcher import RESEARCH_SYNTHESIS_PROMPT_TEMPLATE
from polyplexity_agent.utils.helpers import create_llm_model, format_date, log_node_state

logger = get_logger(__name__)


def _synthesize_research_llm(state: ResearcherState) -> str:
    """Synthesize research results using LLM."""
    raw_data = "\n".join(state["search_results"])
    prompt = RESEARCH_SYNTHESIS_PROMPT_TEMPLATE.format(
        current_date=format_date(),
        topic=state['topic'],
        raw_data=raw_data
    )
    response = create_llm_model().invoke([HumanMessage(content=prompt)])
    return response.content


def synthesize_research_node(state: ResearcherState):
    """Summarizes all search results into a clean research note."""
    try:
        # Access state logger from researcher module temporarily (like Phase 4 pattern)
        from polyplexity_agent.graphs.subgraphs.researcher import _state_logger
        log_node_state(_state_logger, "synthesize_research", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Search results count: {len(state.get('search_results', []))}")
        
        node_call_event = create_trace_event("node_call", "synthesize_research", {})
        synthesis_event = create_trace_event("custom", "synthesize_research", {"event": "research_synthesis_done"})
        
        stream_trace_event("node_call", "synthesize_research", {})
        stream_trace_event("custom", "synthesize_research", {"event": "research_synthesis_done"})
        
        summary = _synthesize_research_llm(state)
        stream_custom_event("research_synthesis_done", "synthesize_research", {"summary": summary[:100] + "..."})
        
        log_node_state(_state_logger, "synthesize_research", "SUBGRAPH", {**state, "research_summary": summary}, "AFTER", additional_info=f"Research summary length: {len(summary)} chars")
        return {"research_summary": summary, "execution_trace": [node_call_event, synthesis_event]}
    except Exception as e:
        stream_custom_event("error", "synthesize_research", {"error": str(e)})
        logger.error("synthesize_research_node_error", error=str(e), exc_info=True)
        raise
