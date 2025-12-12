"""
Rewrite polymarket response node for the main agent graph.

Generates a convincing salesman-like blurb connecting user's question to approved markets.
"""
from langchain_core.messages import HumanMessage

from polyplexity_agent.streaming.event_serializers import create_trace_event
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.prompts.response_generator import POLYMARKET_BLURB_PROMPT_TEMPLATE
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.utils.helpers import create_llm_model, log_node_state

logger = get_logger(__name__)


def _format_markets_info(markets: list) -> str:
    """
    Format approved markets for prompt.

    Args:
        markets: List of market dictionaries.

    Returns:
        Formatted string with market information.
    """
    if not markets:
        return "No markets available."
    formatted = []
    for market in markets[:5]:  # Limit to top 5 markets
        question = market.get("question", "")
        slug = market.get("slug", "")
        formatted.append(f"- {question} (slug: {slug})")
    return "\n".join(formatted)


def _generate_polymarket_blurb(state: SupervisorState) -> str:
    """
    Generate convincing blurb using LLM.

    Args:
        state: The supervisor state.

    Returns:
        Generated blurb text.
    """
    markets = state.get("approved_markets", [])
    markets_info = _format_markets_info(markets)
    final_report = state.get("final_report", "")
    summary = final_report[:500] if len(final_report) > 500 else final_report
    prompt = POLYMARKET_BLURB_PROMPT_TEMPLATE.format(
        user_request=state["user_request"],
        final_report_summary=summary,
        markets_info=markets_info,
    )
    response = create_llm_model().invoke([HumanMessage(content=prompt)])
    return response.content


def rewrite_polymarket_response_node(state: SupervisorState):
    """
    Generate a convincing salesman-like blurb connecting user's question to approved markets.

    Args:
        state: The supervisor state containing user_request, final_report, and approved_markets.

    Returns:
        Dictionary with polymarket_blurb and execution_trace updates.
    """
    try:
        from polyplexity_agent.utils.state_manager import _state_logger
        log_node_state(
            _state_logger,
            "rewrite_polymarket_response",
            "MAIN_GRAPH",
            dict(state),
            "BEFORE",
            state.get("iterations", 0),
            f"Approved markets count: {len(state.get('approved_markets', []))}",
        )
        stream_trace_event("node_call", "rewrite_polymarket_response", {})
        approved_markets = state.get("approved_markets", [])
        if not approved_markets:
            stream_custom_event(
                "polymarket_blurb_skipped",
                "rewrite_polymarket_response",
                {"reason": "no_markets"},
            )
            return {}
        blurb = _generate_polymarket_blurb(state)
        stream_custom_event(
            "polymarket_blurb_generated",
            "rewrite_polymarket_response",
            {"blurb": blurb},
        )
        trace_event = create_trace_event(
            "custom",
            "rewrite_polymarket_response",
            {"event": "polymarket_blurb_complete"},
        )
        result = {"polymarket_blurb": blurb, "execution_trace": [trace_event]}
        log_node_state(
            _state_logger,
            "rewrite_polymarket_response",
            "MAIN_GRAPH",
            {**state, **result},
            "AFTER",
            state.get("iterations", 0),
            f"Blurb length: {len(blurb)} chars",
        )
        return result
    except Exception as e:
        stream_custom_event(
            "error", "rewrite_polymarket_response", {"error": str(e)}
        )
        logger.error(
            "rewrite_polymarket_response_node_error",
            error=str(e),
            exc_info=True,
        )
        raise
