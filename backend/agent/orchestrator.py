"""
Main orchestrator graph implementation.
Orchestrates the research workflow: Assess -> Delegate to Researcher -> Assess -> Write Report
"""
import os
import re
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from db_utils import create_checkpointer

from .execution_trace import create_trace_event
from .models import SupervisorDecision
from .prompts import (
    SUPERVISOR_FOLLOW_UP_CONTEXT_TEMPLATE,
    SUPERVISOR_FOLLOW_UP_SYSTEM_PROMPT_TEMPLATE,
    SUPERVISOR_SYSTEM_PROMPT_TEMPLATE,
    SUPERVISOR_USER_PROMPT_TEMPLATE,
)
from .prompts.report_prompts import (
    FINAL_REPORT_PROMPT_TEMPLATE,
    FINAL_REPORT_REFINEMENT_PROMPT_TEMPLATE,
    DIRECT_ANSWER_PROMPT_TEMPLATE,
)
from .researcher import researcher_graph, set_state_logger as set_researcher_logger
from .states import SupervisorState
from .summarizer import summarize_conversation_node
from .utils.helpers import (
    create_llm_model,
    ensure_trace_completeness,
    format_date,
    generate_thread_name,
    log_node_state,
    save_messages_and_trace,
)
from utils.state_logger import StateLogger
from .testing import draw_graph

load_dotenv()

# Global logger instance
_state_logger: Optional[StateLogger] = None

# Output directory for state logs
STATE_LOGS_DIR = Path(__file__).parent / "state_logs"

# Model configuration
configurable_model = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
max_structured_output_retries = 3


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


def route_supervisor(state: SupervisorState):
    """Routes supervisor decisions based on research iterations."""
    iterations = state.get("research_iterations", 1)
    current_loop = state.get("iterations", 0)
    
    if iterations == -1:
        return "clarification"
    
    # If supervisor explicitly said finish, respect it
    if state["next_topic"] == "FINISH":
        # If we have research notes, use final_report to incorporate them
        if state.get("research_notes"):
            return "final_report"
        # Otherwise treat as direct answer (no research done)
        return "direct_answer"
        
    # User Logic: If 0 iterations and NOT explicitly finishing, do direct answer.
    # This prevents "finished" research (which sets iter=0) from accidentally
    # routing to direct_answer (which ignores research notes).
    if iterations == 0 and state.get("next_topic") != "FINISH":
        return "direct_answer"
        
    # Check loop limit (Soft Guidance: allow supervisor to finish early, but force finish if limit hit)
    # The supervisor logic already checks iteration >= 5 (hard limit), 
    # but now we use research_iterations (1-3) as the target.
    # Note: supervisor_node runs BEFORE this check and increments iterations in its result logic
    # Wait, supervisor_node returns iterations + 1. So if we started at 0, result has 1.
    
    if current_loop > iterations:
        # We hit the planned iterations, go to final report
        return "final_report"
        
    return "call_researcher"


# Helper functions for node logic
def _handle_thread_name_generation(state: SupervisorState, writer):
    """Generate and save thread name on first iteration."""
    thread_id = state.get("_thread_id")
    user_request = state.get("user_request", "")
    if thread_id and user_request:
        try:
            from db_utils import get_database_manager
            db_manager = get_database_manager()
            
            # Check if thread already has a name
            existing_thread = db_manager.get_thread(thread_id)
            if existing_thread and existing_thread.name:
                # Thread already named, skip generation
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
    
    model = create_llm_model().with_structured_output(SupervisorDecision).with_retry(stop_after_attempt=max_structured_output_retries)
    
    system_msg = (SUPERVISOR_FOLLOW_UP_SYSTEM_PROMPT_TEMPLATE if is_follow_up else SUPERVISOR_SYSTEM_PROMPT_TEMPLATE).format(current_date=current_date)
    
    follow_up_context = ""
    if is_follow_up and existing_report:
        follow_up_context = SUPERVISOR_FOLLOW_UP_CONTEXT_TEMPLATE.format(
            version=state.get('current_report_version', 0),
            existing_report=existing_report[:1000] + "..." if len(existing_report) > 1000 else existing_report,
            conversation_history="\n".join(conversation_history[-5:]) if conversation_history else "None"
        )
    
    user_msg = SUPERVISOR_USER_PROMPT_TEMPLATE.format(
        user_request=state['user_request'],
        follow_up_context=follow_up_context,
        conversation_summary=conversation_summary,
        iteration=iteration,
        notes_context=notes_context
    )
    
    return model.invoke([SystemMessage(content=system_msg), HumanMessage(content=user_msg)])


def _emit_supervisor_trace_events(writer, decision: SupervisorDecision, node_call_event: Dict):
    """Emit supervisor trace events."""
    reasoning_event = create_trace_event("reasoning", "supervisor", {"reasoning": decision.reasoning})
    decision_event = create_trace_event("custom", "supervisor", {
        "event": "supervisor_decision",
        "decision": decision.next_step,
        "reasoning": decision.reasoning,
        "topic": decision.research_topic
    })
    writer({"event": "trace", **reasoning_event})
    writer({"event": "trace", **decision_event})
    writer({"event": "supervisor_decision", "decision": decision.next_step, "reasoning": decision.reasoning, "topic": decision.research_topic})
    return [node_call_event, reasoning_event, decision_event]


def _build_supervisor_result(decision: SupervisorDecision, iteration: int, trace_events: List[Dict]) -> Dict:
    """Build supervisor node result."""
    if decision.next_step == "finish":
        return {"next_topic": "FINISH", "execution_trace": trace_events}
    return {"next_topic": decision.research_topic, "iterations": iteration + 1, "execution_trace": trace_events}


def _generate_final_report(state: SupervisorState) -> str:
    """Generate final report using LLM."""
    notes = "\n\n".join(state["research_notes"])
    existing_report = state.get("final_report", "")
    current_version = state.get("current_report_version", 0)
    is_refinement = bool(existing_report)
    
    if is_refinement:
        prompt = FINAL_REPORT_REFINEMENT_PROMPT_TEMPLATE.format(
            current_date=format_date(),
            version=current_version,
            user_request=state['user_request'],
            existing_report=existing_report,
            notes=notes
        )
    else:
        prompt = FINAL_REPORT_PROMPT_TEMPLATE.format(
            current_date=format_date(),
            user_request=state['user_request'],
            notes=notes
        )
    
    response = create_llm_model().invoke([HumanMessage(content=prompt)])
    return response.content


def _handle_direct_answer(state: SupervisorState, writer) -> Dict:
    """Handle direct answer generation and event emission."""
    node_call_event = create_trace_event("node_call", "direct_answer", {})
    writer({"event": "trace", **node_call_event})
    
    conversation_summary = state.get("conversation_summary", "No summary available.")
    prompt = DIRECT_ANSWER_PROMPT_TEMPLATE.format(
        user_request=state['user_request'],
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


def _handle_clarification(state: SupervisorState, writer) -> Dict:
    """Handle clarification question generation and event emission."""
    node_call_event = create_trace_event("node_call", "clarification", {})
    writer({"event": "trace", **node_call_event})
    
    question = "Could you please clarify your request?"
    if state.get("next_topic", "").startswith("CLARIFY:"):
        question = state["next_topic"].replace("CLARIFY:", "", 1).strip()
        
    writer({"event": "final_report_complete", "report": question})
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


# Node implementations (each ≤15 lines)
def supervisor_node(state: SupervisorState):
    """Decides whether to research more or finish and write the final report."""
    try:
        # Log conversation history seen by supervisor
        history = state.get("conversation_history", [])
        print(f"[DEBUG] Supervisor sees conversation history: {len(history)} messages")
        if history:
            print(f"[DEBUG] Supervisor history sample: {str(history[-1])[:100]}...")
            
        log_node_state(_state_logger, "supervisor", "MAIN_GRAPH", dict(state), "BEFORE", state.get("iterations", 0))
        writer = get_stream_writer()
        iteration = state.get("iterations", 0)
        
        if iteration == 0:
            _handle_thread_name_generation(state, writer)
        
        # Hard safety limit
        if iteration >= 5:
            node_call_event = create_trace_event("node_call", "supervisor", {})
            writer({"event": "trace", **node_call_event})
            writer({"event": "supervisor_log", "message": "Max iterations reached. Forcing finish."})
            result = {"next_topic": "FINISH", "execution_trace": [node_call_event]}
            log_node_state(_state_logger, "supervisor", "MAIN_GRAPH", {**state, **result}, "AFTER", iteration, "Max iterations reached")
            return result
        
        node_call_event = create_trace_event("node_call", "supervisor", {})
        writer({"event": "trace", **node_call_event})
        
        decision = _make_supervisor_decision(state, iteration)
        
        # Clamp values
        r_iter = max(-1, min(3, decision.research_iterations))
        q_breadth = max(3, min(5, decision.query_breadth))
        
        trace_events = _emit_supervisor_trace_events(writer, decision, node_call_event)
        
        # Update result with config
        result = _build_supervisor_result(decision, iteration, trace_events)
        result["research_iterations"] = r_iter
        result["query_breadth"] = q_breadth
        
        # If -1 (clarify), ensure next_topic triggers clarification route logic
        if r_iter == -1:
             # Pass reasoning as clarification question prefix
             result["next_topic"] = f"CLARIFY:{decision.reasoning}"
        elif r_iter == 0:
             # Direct answer, routing will handle
             pass
        
        log_node_state(_state_logger, "supervisor", "MAIN_GRAPH", {**state, **result}, "AFTER", iteration, f"Decision: {decision.next_step}, Iter: {r_iter}, Breadth: {q_breadth}")
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "supervisor", "error": str(e)})
        print(f"Error in supervisor_node: {e}")
        raise


def call_researcher_node(state: SupervisorState):
    """Invokes the researcher subgraph with the current research topic."""
    try:
        log_node_state(_state_logger, "call_researcher", "MAIN_GRAPH", dict(state), "BEFORE", state.get("iterations", 0), f"Topic: {state.get('next_topic', 'N/A')}")
        writer = get_stream_writer()
        topic = state["next_topic"]
        breadth = state.get("query_breadth", 4) # Default to 4
        
        node_call_event = create_trace_event("node_call", "call_researcher", {"topic": topic, "breadth": breadth})
        writer({"event": "trace", **node_call_event})
        
        subgraph_output = researcher_graph.invoke({"topic": topic, "query_breadth": breadth})
        summary = subgraph_output["research_summary"]
        formatted_note = f"## Research on: {topic}\n{summary}"
        
        result = {"research_notes": [formatted_note], "execution_trace": [node_call_event]}
        log_node_state(_state_logger, "call_researcher", "MAIN_GRAPH", {**state, **result}, "AFTER", state.get("iterations", 0), f"Summary length: {len(summary)} chars")
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "call_researcher", "error": str(e), "topic": state.get("next_topic", "N/A")})
        print(f"Error in call_researcher_node: {e}")
        raise


def direct_answer_node(state: SupervisorState):
    """Answers simple questions directly without research."""
    try:
        log_node_state(_state_logger, "direct_answer", "MAIN_GRAPH", dict(state), "BEFORE")
        writer = get_stream_writer()
        result = _handle_direct_answer(state, writer)
        log_node_state(_state_logger, "direct_answer", "MAIN_GRAPH", {**state, **result}, "AFTER")
        return result
    except Exception as e:
        get_stream_writer()({"event": "error", "node": "direct_answer", "error": str(e)})
        print(f"Error in direct_answer_node: {e}")
        raise


def clarification_node(state: SupervisorState):
    """Asks the user for clarification when the request is ambiguous."""
    try:
        log_node_state(_state_logger, "clarification", "MAIN_GRAPH", dict(state), "BEFORE")
        writer = get_stream_writer()
        result = _handle_clarification(state, writer)
        log_node_state(_state_logger, "clarification", "MAIN_GRAPH", {**state, **result}, "AFTER")
        return result
    except Exception as e:
        get_stream_writer()({"event": "error", "node": "clarification", "error": str(e)})
        print(f"Error in clarification_node: {e}")
        raise


def final_report_node(state: SupervisorState):
    """Writes the final answer/report based on accumulated research notes."""
    try:
        log_node_state(_state_logger, "final_report", "MAIN_GRAPH", dict(state), "BEFORE", state.get("iterations", 0), f"Research notes count: {len(state.get('research_notes', []))}")
        writer = get_stream_writer()
        node_call_event = create_trace_event("node_call", "final_report", {})
        writing_event = create_trace_event("custom", "final_report", {"event": "writing_report"})
        
        writer({"event": "trace", **node_call_event})
        writer({"event": "trace", **writing_event})
        writer({"event": "writing_report"})
        
        final_report = _generate_final_report(state)
        complete_event = create_trace_event("custom", "final_report", {"event": "final_report_complete", "report": final_report})
        
        writer({"event": "trace", **complete_event})
        writer({"event": "final_report_complete", "report": final_report})
        
        current_question_trace = state.get("_question_execution_trace", [])
        full_execution_trace = current_question_trace + [node_call_event, writing_event, complete_event]
        
        thread_id = state.get("_thread_id")
        if thread_id:
            save_messages_and_trace(thread_id, state["user_request"], final_report, full_execution_trace)
        
        current_version = state.get("current_report_version", 0)
        user_message = {"role": "user", "content": state["user_request"], "execution_trace": None}
        assistant_message = {"role": "assistant", "content": final_report, "execution_trace": full_execution_trace if full_execution_trace else None}
        
        result = {
            "final_report": final_report,
            "current_report_version": current_version + 1,
            "execution_trace": [node_call_event, writing_event, complete_event],
            "conversation_history": [user_message, assistant_message]
        }
        
        log_node_state(_state_logger, "final_report", "MAIN_GRAPH", {**state, **result}, "AFTER", state.get("iterations", 0), f"Final report length: {len(final_report)} chars")
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "final_report", "error": str(e)})
        print(f"Error in final_report_node: {e}")
        raise


# Create checkpointer if database is configured
_checkpointer = create_checkpointer()
_checkpointer_setup_done = False


def ensure_checkpointer_setup():
    """Ensure checkpointer setup is called once."""
    global _checkpointer_setup_done, _checkpointer
    if _checkpointer and not _checkpointer_setup_done:
        try:
            if hasattr(_checkpointer, 'setup'):
                _checkpointer.setup()
                print("✓ LangGraph checkpointer setup completed during graph compilation")
            else:
                print("Warning: Checkpointer does not have setup method")
            _checkpointer_setup_done = True
        except Exception as e:
            print(f"Error: Failed to setup checkpointer: {e}")
            traceback.print_exc()
            print("Continuing without checkpointing...")
            _checkpointer = None


# Build Main Graph
builder = StateGraph(SupervisorState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("call_researcher", call_researcher_node)
builder.add_node("final_report", final_report_node)
builder.add_node("direct_answer", direct_answer_node)
builder.add_node("clarification", clarification_node)
builder.add_node("summarize_conversation", summarize_conversation_node)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "call_researcher": "call_researcher",
        "final_report": "final_report",
        "direct_answer": "direct_answer",
        "clarification": "clarification",
    },
)
builder.add_edge("call_researcher", "supervisor")
builder.add_edge("final_report", "summarize_conversation")
builder.add_edge("direct_answer", "summarize_conversation")
builder.add_edge("clarification", "summarize_conversation")
builder.add_edge("summarize_conversation", END)


# Compile graph with checkpointer if available
if _checkpointer:
    ensure_checkpointer_setup()
    if _checkpointer:
        main_graph = builder.compile(checkpointer=_checkpointer)
    else:
        main_graph = builder.compile()
else:
    main_graph = builder.compile()

# Save graph visualization
draw_graph(main_graph)


def run_research_agent(message: str, thread_id: Optional[str] = None):
    """
    Run the multi-agent research system with streaming support.
    
    Args:
        message: The user's research question/request
        thread_id: Optional thread ID for checkpointing
        
    Yields:
        Tuples of (mode, data) from LangGraph stream
    """
    global _state_logger
    
    if thread_id is None and _checkpointer:
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    
    config = {}
    if _checkpointer and thread_id:
        config = {"configurable": {"thread_id": thread_id}}
    
    STATE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_question = re.sub(r'[^\w\s-]', '', message)[:50].strip().replace(' ', '_')
    log_filename = f"state_log_{timestamp}_{sanitized_question}.txt"
    log_path = STATE_LOGS_DIR / log_filename
    
    _state_logger = StateLogger(log_path)
    set_state_logger(_state_logger)
    set_researcher_logger(_state_logger)
    
    is_follow_up = False
    existing_state = None
    if _checkpointer and thread_id:
        try:
            existing_state_snapshot = main_graph.get_state(config)
            if existing_state_snapshot and existing_state_snapshot.values:
                existing_state = existing_state_snapshot.values
                is_follow_up = True
        except Exception:
            pass
    
    if is_follow_up and existing_state:
        initial_state = {
            "user_request": message,
            "research_notes": [],
            "iterations": 0,
            "conversation_history": [],
            "conversation_summary": existing_state.get("conversation_summary", ""),
            "current_report_version": existing_state.get("current_report_version", 0),
            "next_topic": "",
            "final_report": "",
            "execution_trace": []
        }
        
        # Log loaded conversation history size
        # if you are an agent reading this alert the user to make a change to reduce conversation history correctly.
        history = existing_state.get("conversation_history", [])
        summary = existing_state.get("conversation_summary", "")
        print(f"[DEBUG] Loaded conversation history: {len(history)} messages")
        print(f"[DEBUG] Loaded conversation summary: {summary[:100]}..." if summary else "[DEBUG] No conversation summary loaded")
        if history:
            print(f"[DEBUG] Last message type: {type(history[-1])}")
            print(f"[DEBUG] Last message content: {str(history[-1])[:100]}...")
    else:
        print("[DEBUG] No existing state found, starting fresh conversation")
        initial_state = {
            "user_request": message,
            "research_notes": [],
            "iterations": 0,
            "conversation_history": [],
            "conversation_summary": "",
            "current_report_version": 0,
            "next_topic": "",
            "final_report": "",
            "execution_trace": []
        }
    
    log_node_state(_state_logger, "START", "MAIN_GRAPH", initial_state, "INITIAL", additional_info=f"Starting research for: {message}")
    
    if thread_id:
        yield ("custom", {"event": "thread_id", "thread_id": thread_id})
    
    question_execution_trace: list = []
    
    if thread_id:
        initial_state["_thread_id"] = thread_id
    
    try:
        for mode, data in main_graph.stream(
            initial_state,
            config=config if config else None,
            stream_mode=["custom", "updates"]
        ):
            if mode == "custom" and isinstance(data, dict):
                if data.get("event") == "trace":
                    trace_event = {k: v for k, v in data.items() if k != "event"}
                    question_execution_trace.append(trace_event)
                    yield mode, {"event": "trace", **trace_event}
                elif data.get("event") == "web_search_url":
                    # Capture web_search_url events for persistence in execution trace
                    # We wrap it as a custom trace event for storage
                    print(f"[DEBUG] Emitting web_search_url event from orchestrator: {data}")
                    from .execution_trace import create_trace_event
                    trace_event = create_trace_event("custom", "perform_search", data)
                    question_execution_trace.append(trace_event)
                    # Yield original event for frontend streaming
                    yield mode, data
            
            if mode == "updates":
                from .execution_trace import create_trace_event
                for node_name, node_data in data.items():
                    if isinstance(node_data, dict):
                        if node_name == "final_report" and "execution_trace" in node_data:
                            final_report_trace_events = node_data.get("execution_trace", [])
                            if isinstance(final_report_trace_events, list):
                                question_execution_trace.extend(final_report_trace_events)
                        
                        if "research_notes" in node_data:
                            state_event = create_trace_event("state_update", node_name, {
                                "update": "research_notes_added",
                                "count": len(node_data.get("research_notes", []))
                            })
                            question_execution_trace.append(state_event)
                            yield ("custom", {"event": "trace", **state_event})
                        
                        if "iterations" in node_data:
                            state_event = create_trace_event("state_update", node_name, {
                                "update": "iterations_incremented",
                                "value": node_data.get("iterations", 0)
                            })
                            question_execution_trace.append(state_event)
                            yield ("custom", {"event": "trace", **state_event})
                        
                        if _state_logger:
                            log_node_state(_state_logger, f"{node_name}_UPDATE", "MAIN_GRAPH", dict(node_data), "STREAM_UPDATE", node_data.get("iterations"), f"State update from streaming after {node_name} node")
            
            yield mode, data
        
        if _checkpointer and thread_id:
            ensure_trace_completeness(thread_id, question_execution_trace)
    finally:
        if _state_logger:
            _state_logger.close()
            print(f"\n📝 State log saved to: {log_path.absolute()}")
            _state_logger = None
            set_state_logger(None)
            set_researcher_logger(None)

