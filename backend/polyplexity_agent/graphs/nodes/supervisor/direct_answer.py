"""
Direct answer node for the main agent graph.

Answers simple questions directly without research.
"""
from typing import Dict

from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer

from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.prompts.response_generator import DIRECT_ANSWER_PROMPT_TEMPLATE
from polyplexity_agent.utils.helpers import create_llm_model, log_node_state, save_messages_and_trace


def _handle_direct_answer(state: SupervisorState, writer) -> Dict:
    """Handle direct answer generation and event emission."""
    node_call_event = create_trace_event("node_call", "direct_answer", {})
    writer({"event": "trace", **node_call_event})
    conversation_summary = state.get("conversation_summary", "No summary available.")
    prompt = DIRECT_ANSWER_PROMPT_TEMPLATE.format(
        user_request=state["user_request"],
        conversation_summary=conversation_summary
    )
    final_answer = create_llm_model().invoke([HumanMessage(content=prompt)]).content
    complete_event = create_trace_event("custom", "direct_answer", {"event": "final_report_complete", "report": final_answer})
    writer({"event": "trace", **complete_event})
    writer({"event": "final_report_complete", "report": final_answer})
    full_trace = state.get("_question_execution_trace", []) + [node_call_event, complete_event]
    if state.get("_thread_id"):
        save_messages_and_trace(state["_thread_id"], state["user_request"], final_answer, full_trace)
    user_msg = {"role": "user", "content": state["user_request"], "execution_trace": None}
    asst_msg = {"role": "assistant", "content": final_answer, "execution_trace": full_trace}
    return {
        "final_report": final_answer,
        "current_report_version": state.get("current_report_version", 0) + 1,
        "execution_trace": [node_call_event, complete_event],
        "conversation_history": [user_msg, asst_msg],
        "next_topic": "FINISH"
    }


def direct_answer_node(state: SupervisorState):
    """Answers simple questions directly without research."""
    try:
        from polyplexity_agent.orchestrator import _state_logger
        log_node_state(_state_logger, "direct_answer", "MAIN_GRAPH", dict(state), "BEFORE")
        writer = get_stream_writer()
        result = _handle_direct_answer(state, writer)
        log_node_state(_state_logger, "direct_answer", "MAIN_GRAPH", {**state, **result}, "AFTER")
        return result
    except Exception as e:
        get_stream_writer()({"event": "error", "node": "direct_answer", "error": str(e)})
        print(f"Error in direct_answer_node: {e}")
        raise
