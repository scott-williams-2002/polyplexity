"""
Clarification node for the main agent graph.

Asks the user for clarification when the request is ambiguous.
"""
from typing import Dict

from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.utils.helpers import log_node_state, save_messages_and_trace


def _handle_clarification(state: SupervisorState) -> Dict:
    """Handle clarification question generation and event emission."""
    node_call_event = create_trace_event("node_call", "clarification", {})
    stream_trace_event("node_call", "clarification", {})
    question = "Could you please clarify your request?"
    if state.get("next_topic", "").startswith("CLARIFY:"):
        question = state["next_topic"].replace("CLARIFY:", "", 1).strip()
    stream_custom_event("final_report_complete", "clarification", {"report": question})
    full_trace = state.get("_question_execution_trace", []) + [node_call_event]
    if state.get("_thread_id"):
        save_messages_and_trace(state["_thread_id"], state["user_request"], question, full_trace)
    user_msg = {"role": "user", "content": state["user_request"], "execution_trace": None}
    asst_msg = {"role": "assistant", "content": question, "execution_trace": full_trace}
    return {
        "final_report": question,
        "current_report_version": state.get("current_report_version", 0),
        "execution_trace": [node_call_event],
        "conversation_history": [user_msg, asst_msg],
        "next_topic": "FINISH"
    }


def clarification_node(state: SupervisorState):
    """Asks the user for clarification when the request is ambiguous."""
    try:
        from polyplexity_agent.orchestrator import _state_logger
        log_node_state(_state_logger, "clarification", "MAIN_GRAPH", dict(state), "BEFORE")
        result = _handle_clarification(state)
        log_node_state(_state_logger, "clarification", "MAIN_GRAPH", {**state, **result}, "AFTER")
        return result
    except Exception as e:
        stream_custom_event("error", "clarification", {"error": str(e)})
        print(f"Error in clarification_node: {e}")
        raise
