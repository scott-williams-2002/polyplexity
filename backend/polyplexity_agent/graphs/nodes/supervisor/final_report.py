"""
Final report node for the main agent graph.

Writes the final answer/report based on accumulated research notes.
"""
from langchain_core.messages import HumanMessage
from langgraph.config import get_stream_writer

from polyplexity_agent.config import Settings
from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.prompts.response_generator import (
    FINAL_RESPONSE_PROMPT_TEMPLATE,
    FINAL_RESPONSE_REFINEMENT_PROMPT_TEMPLATE,
    FORMAT_INSTRUCTIONS_CONCISE,
    FORMAT_INSTRUCTIONS_REPORT,
)
from polyplexity_agent.utils.helpers import create_llm_model, format_date, log_node_state, save_messages_and_trace

settings = Settings()


def _generate_final_report(state: SupervisorState) -> str:
    """Generate final report using LLM."""
    notes = "\n\n".join(state["research_notes"])
    existing_report = state.get("final_report", "")
    current_version = state.get("current_report_version", 0)
    is_refinement = bool(existing_report)
    answer_format = state.get("answer_format", "concise")
    formatting_instructions = FORMAT_INSTRUCTIONS_REPORT if answer_format == "report" else FORMAT_INSTRUCTIONS_CONCISE
    if is_refinement:
        prompt = FINAL_RESPONSE_REFINEMENT_PROMPT_TEMPLATE.format(
            current_date=format_date(),
            version=current_version,
            user_request=state["user_request"],
            existing_report=existing_report,
            notes=notes,
            formatting_instructions=formatting_instructions
        )
    else:
        prompt = FINAL_RESPONSE_PROMPT_TEMPLATE.format(
            current_date=format_date(),
            user_request=state["user_request"],
            notes=notes,
            formatting_instructions=formatting_instructions
        )
    response = create_llm_model().invoke([HumanMessage(content=prompt)])
    return response.content


def final_report_node(state: SupervisorState):
    """Writes the final answer/report based on accumulated research notes."""
    try:
        from polyplexity_agent.orchestrator import _state_logger
        log_node_state(_state_logger, "final_report", "MAIN_GRAPH", dict(state), "BEFORE", state.get("iterations", 0), f"Research notes count: {len(state.get('research_notes', []))}")
        writer = get_stream_writer()
        node_call_event = create_trace_event("node_call", "final_report", {})
        writer({"event": "trace", **node_call_event})
        writer({"event": "writing_report"})
        final_report = _generate_final_report(state)
        complete_event = create_trace_event("custom", "final_report", {"event": "final_report_complete", "report": final_report})
        writer({"event": "trace", **complete_event})
        writer({"event": "final_report_complete", "report": final_report})
        current_question_trace = state.get("_question_execution_trace", [])
        full_execution_trace = current_question_trace + [node_call_event, complete_event]
        thread_id = state.get("_thread_id")
        if thread_id:
            save_messages_and_trace(thread_id, state["user_request"], final_report, full_execution_trace)
        current_version = state.get("current_report_version", 0)
        user_message = {"role": "user", "content": state["user_request"], "execution_trace": None}
        assistant_message = {"role": "assistant", "content": final_report, "execution_trace": full_execution_trace if full_execution_trace else None}
        result = {
            "final_report": final_report,
            "current_report_version": current_version + 1,
            "execution_trace": [node_call_event, complete_event],
            "conversation_history": [user_message, assistant_message]
        }
        log_node_state(_state_logger, "final_report", "MAIN_GRAPH", {**state, **result}, "AFTER", state.get("iterations", 0), f"Final report length: {len(final_report)} chars")
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "final_report", "error": str(e)})
        print(f"Error in final_report_node: {e}")
        raise
