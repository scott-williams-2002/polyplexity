"""
Call market research node for the main agent graph.

Invokes the market research subgraph with user question and final report.
"""
from polyplexity_agent.streaming.event_serializers import create_trace_event
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.graphs.subgraphs.market_research import market_research_graph
from polyplexity_agent.logging import get_logger
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.utils.helpers import log_node_state

logger = get_logger(__name__)


def call_market_research_node(state: SupervisorState):
    """
    Invokes the market research subgraph with user question and final report.

    Args:
        state: The supervisor state containing user_request and final_report.

    Returns:
        Dictionary with approved_markets and execution_trace updates.
    """
    try:
        from polyplexity_agent.utils.state_manager import _state_logger
        log_node_state(
            _state_logger,
            "call_market_research",
            "MAIN_GRAPH",
            dict(state),
            "BEFORE",
            state.get("iterations", 0),
            f"User request: {state.get('user_request', 'N/A')[:50]}",
        )
        user_request = state["user_request"]
        final_report = state.get("final_report", "")
        node_call_event = create_trace_event(
            "node_call", "call_market_research", {"user_request": user_request}
        )
        stream_trace_event("node_call", "call_market_research", {})
        stream_custom_event(
            "market_research_start",
            "call_market_research",
            {"user_request": user_request},
        )
        approved_markets = []
        for mode, data in market_research_graph.stream(
            {"original_topic": user_request, "ai_response": final_report},
            stream_mode=["custom", "values"],
        ):
            logger.debug(
                "market_research_graph_stream_chunk", mode=mode, data_type=str(type(data))
            )
            if mode == "custom":
                items = data if isinstance(data, list) else [data]
                for item in items:
                    from langgraph.config import get_stream_writer

                    writer = get_stream_writer()
                    if writer:
                        writer(item)
            elif mode == "values":
                if "approved_markets" in data:
                    approved_markets = data["approved_markets"]
        result = {"approved_markets": approved_markets, "execution_trace": [node_call_event]}
        log_node_state(
            _state_logger,
            "call_market_research",
            "MAIN_GRAPH",
            {**state, **result},
            "AFTER",
            state.get("iterations", 0),
            f"Approved markets count: {len(approved_markets)}",
        )
        return result
    except Exception as e:
        stream_custom_event(
            "error", "call_market_research", {"error": str(e)}
        )
        logger.error(
            "call_market_research_node_error",
            error=str(e),
            exc_info=True,
        )
        raise
