"""
Supervisor node for the main agent graph.

Decides whether to research more, finish, or ask for clarification.
"""
from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer

from polyplexity_agent.config import Settings
from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.models import SupervisorDecision
from polyplexity_agent.prompts.supervisor import (
    SUPERVISOR_FOLLOW_UP_CONTEXT_TEMPLATE,
    SUPERVISOR_FOLLOW_UP_SYSTEM_PROMPT_TEMPLATE,
    SUPERVISOR_SYSTEM_PROMPT_TEMPLATE,
    SUPERVISOR_USER_PROMPT_TEMPLATE,
)
from polyplexity_agent.utils.helpers import (
    create_llm_model,
    format_date,
    generate_thread_name,
    log_node_state,
)

settings = Settings()


def _handle_thread_name_generation(state: SupervisorState, writer):
    """Generate and save thread name on first iteration."""
    thread_id = state.get("_thread_id")
    user_request = state.get("user_request", "")
    if thread_id and user_request:
        try:
            from polyplexity_agent.db_utils import get_database_manager
            db_manager = get_database_manager()
            existing_thread = db_manager.get_thread(thread_id)
            if existing_thread and existing_thread.name:
                return
            thread_name = generate_thread_name(user_request)
            db_manager.save_thread_name(thread_id, thread_name)
            writer({"event": "thread_name", "thread_id": thread_id, "name": thread_name})
        except Exception as e:
            print(f"Warning: Failed to handle thread name generation: {e}")


def _make_supervisor_decision(state: SupervisorState, iteration: int) -> SupervisorDecision:
    """Make supervisor decision using LLM."""
    notes_context = "\n\n".join(state.get("research_notes", []))
    current_date = format_date()
    is_follow_up = bool(state.get("final_report") or state.get("conversation_history"))
    existing_report = state.get("final_report", "")
    conversation_history = state.get("conversation_history", [])
    conversation_summary = state.get("conversation_summary", "None")
    model = create_llm_model().with_structured_output(SupervisorDecision).with_retry(stop_after_attempt=settings.max_structured_output_retries)
    system_msg = (SUPERVISOR_FOLLOW_UP_SYSTEM_PROMPT_TEMPLATE if is_follow_up else SUPERVISOR_SYSTEM_PROMPT_TEMPLATE).format(current_date=current_date)
    follow_up_context = ""
    if is_follow_up and existing_report:
        follow_up_context = SUPERVISOR_FOLLOW_UP_CONTEXT_TEMPLATE.format(
            version=state.get("current_report_version", 0),
            existing_report=existing_report[:1000] + "..." if len(existing_report) > 1000 else existing_report,
            conversation_history="\n".join(conversation_history[-5:]) if conversation_history else "None"
        )
    user_msg = SUPERVISOR_USER_PROMPT_TEMPLATE.format(
        user_request=state["user_request"],
        follow_up_context=follow_up_context,
        conversation_summary=conversation_summary,
        iteration=iteration,
        notes_context=notes_context
    )
    return model.invoke([SystemMessage(content=system_msg), HumanMessage(content=user_msg)])


def _emit_supervisor_trace_events(writer, decision: SupervisorDecision, node_call_event: Dict):
    """Emit supervisor trace events."""
    reasoning_event = create_trace_event("reasoning", "supervisor", {"reasoning": decision.reasoning})
    writer({"event": "trace", **reasoning_event})
    writer({"event": "supervisor_decision", "decision": decision.next_step, "reasoning": decision.reasoning, "topic": decision.research_topic})
    return [node_call_event, reasoning_event]


def supervisor_node(state: SupervisorState):
    """Decides whether to research more or finish and write the final report."""
    try:
        from polyplexity_agent.orchestrator import _state_logger
        history = state.get("conversation_history", [])
        print(f"[DEBUG] Supervisor sees conversation history: {len(history)} messages")
        if history:
            print(f"[DEBUG] Supervisor history sample: {str(history[-1])[:100]}...")
        log_node_state(_state_logger, "supervisor", "MAIN_GRAPH", dict(state), "BEFORE", state.get("iterations", 0))
        writer = get_stream_writer()
        iteration = state.get("iterations", 0)
        if iteration == 0:
            _handle_thread_name_generation(state, writer)
        if iteration >= 10:
            node_call_event = create_trace_event("node_call", "supervisor", {})
            writer({"event": "trace", **node_call_event})
            writer({"event": "supervisor_log", "message": "Max iterations reached. Forcing finish."})
            result = {"next_topic": "FINISH", "execution_trace": [node_call_event]}
            log_node_state(_state_logger, "supervisor", "MAIN_GRAPH", {**state, **result}, "AFTER", iteration, "Max iterations reached")
            return result
        node_call_event = create_trace_event("node_call", "supervisor", {})
        writer({"event": "trace", **node_call_event})
        decision = _make_supervisor_decision(state, iteration)
        ans_fmt = decision.answer_format if hasattr(decision, "answer_format") and decision.answer_format in ["concise", "report"] else "concise"
        trace_events = _emit_supervisor_trace_events(writer, decision, node_call_event)
        next_topic = decision.research_topic
        if decision.next_step == "clarify":
            next_topic = f"CLARIFY:{decision.reasoning}"
        elif decision.next_step == "finish":
            next_topic = "FINISH"
        result = {
            "next_topic": next_topic,
            "iterations": iteration + 1 if decision.next_step == "research" else iteration,
            "execution_trace": trace_events,
            "answer_format": ans_fmt
        }
        log_node_state(_state_logger, "supervisor", "MAIN_GRAPH", {**state, **result}, "AFTER", iteration, f"Decision: {decision.next_step}, Iter: {iteration}, Format: {ans_fmt}")
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "supervisor", "error": str(e)})
        print(f"Error in supervisor_node: {e}")
        raise
