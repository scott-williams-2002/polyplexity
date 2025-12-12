"""
Call researcher node for the main agent graph.

Invokes the researcher subgraph with the current research topic.
"""
from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.graphs.subgraphs.researcher import researcher_graph
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.utils.helpers import log_node_state


def call_researcher_node(state: SupervisorState):
    """Invokes the researcher subgraph with the current research topic."""
    try:
        from polyplexity_agent.orchestrator import _state_logger
        log_node_state(_state_logger, "call_researcher", "MAIN_GRAPH", dict(state), "BEFORE", state.get("iterations", 0), f"Topic: {state.get('next_topic', 'N/A')}")
        topic = state["next_topic"]
        answer_format = state.get("answer_format", "concise")
        breadth = 3 if answer_format == "concise" else 5
        node_call_event = create_trace_event("node_call", "call_researcher", {"topic": topic, "breadth": breadth})
        stream_trace_event("node_call", "call_researcher", {"topic": topic, "breadth": breadth})
        seen_urls = set()
        final_summary = ""
        for mode, data in researcher_graph.stream(
            {"topic": topic, "query_breadth": breadth},
            stream_mode=["custom", "values"]
        ):
            print(f"[DEBUG] researcher_graph stream chunk: mode={mode}, type(data)={type(data)}")
            if mode == "custom":
                items = data if isinstance(data, list) else [data]
                for item in items:
                    event_type = item.get("event", "unknown")
                    print(f"[DEBUG] Forwarding custom event from researcher: {event_type}")
                    if event_type == "web_search_url":
                        url = item.get("url")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            # Forward event from subgraph (will be normalized if needed)
                            from langgraph.config import get_stream_writer
                            writer = get_stream_writer()
                            if writer:
                                writer(item)
                        else:
                            print(f"[DEBUG] Skipping duplicate web_search_url: {url}")
                    else:
                        # Forward event from subgraph (will be normalized if needed)
                        from langgraph.config import get_stream_writer
                        writer = get_stream_writer()
                        if writer:
                            writer(item)
            elif mode == "values":
                if "research_summary" in data:
                    final_summary = data["research_summary"]
        formatted_note = f"## Research on: {topic}\n{final_summary}"
        result = {"research_notes": [formatted_note], "execution_trace": [node_call_event]}
        log_node_state(_state_logger, "call_researcher", "MAIN_GRAPH", {**state, **result}, "AFTER", state.get("iterations", 0), f"Summary length: {len(final_summary)} chars")
        return result
    except Exception as e:
        stream_custom_event("error", "call_researcher", {"error": str(e), "topic": state.get("next_topic", "N/A")})
        print(f"Error in call_researcher_node: {e}")
        raise
