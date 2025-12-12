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

from polyplexity_agent.config import Settings
from polyplexity_agent.config.secrets import create_checkpointer

from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.models import SupervisorDecision
from polyplexity_agent.prompts.supervisor import (
    SUPERVISOR_FOLLOW_UP_CONTEXT_TEMPLATE,
    SUPERVISOR_FOLLOW_UP_SYSTEM_PROMPT_TEMPLATE,
    SUPERVISOR_SYSTEM_PROMPT_TEMPLATE,
    SUPERVISOR_USER_PROMPT_TEMPLATE,
)
from polyplexity_agent.prompts.response_generator import (
    FINAL_RESPONSE_PROMPT_TEMPLATE,
    FINAL_RESPONSE_REFINEMENT_PROMPT_TEMPLATE,
    DIRECT_ANSWER_PROMPT_TEMPLATE,
    FORMAT_INSTRUCTIONS_CONCISE,
    FORMAT_INSTRUCTIONS_REPORT,
)
from polyplexity_agent.researcher import researcher_graph, set_state_logger as set_researcher_logger
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.summarizer import summarize_conversation_node
from polyplexity_agent.utils.helpers import (
    create_llm_model,
    ensure_trace_completeness,
    format_date,
    generate_thread_name,
    log_node_state,
    save_messages_and_trace,
)
from polyplexity_agent.utils.state_logger import StateLogger

load_dotenv()

# Application settings
settings = Settings()

# Global logger instance
_state_logger: Optional[StateLogger] = None


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


def route_supervisor(state: SupervisorState):
    """Routes based on next_topic and answer_format constraints."""
    next_topic = state.get("next_topic", "")
    answer_format = state.get("answer_format", "concise")
    current_loop = state.get("iterations", 0)

    if next_topic.startswith("CLARIFY:"):
        return "clarification"

    if next_topic == "FINISH":
        if state.get("research_notes"):
            return "final_report"
        return "direct_answer"
    
    # Research path requested
    # Check limits
    if answer_format == "concise":
        if current_loop >= 1:
            # Enforce max 1 loop for concise
            return "final_report"
    else:
        # Report format - default max 5
        if current_loop >= 5:
            return "final_report"

    return "call_researcher"


# Helper functions for node logic
def _handle_thread_name_generation(state: SupervisorState, writer):
    """Generate and save thread name on first iteration."""
    thread_id = state.get("_thread_id")
    user_request = state.get("user_request", "")
    if thread_id and user_request:
        try:
            from polyplexity_agent.db_utils import get_database_manager
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
    
    model = create_llm_model().with_structured_output(SupervisorDecision).with_retry(stop_after_attempt=settings.max_structured_output_retries)
    
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
    writer({"event": "trace", **reasoning_event})
    writer({"event": "supervisor_decision", "decision": decision.next_step, "reasoning": decision.reasoning, "topic": decision.research_topic})
    return [node_call_event, reasoning_event]



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
            user_request=state['user_request'],
            existing_report=existing_report,
            notes=notes,
            formatting_instructions=formatting_instructions
        )
    else:
        prompt = FINAL_RESPONSE_PROMPT_TEMPLATE.format(
            current_date=format_date(),
            user_request=state['user_request'],
            notes=notes,
            formatting_instructions=formatting_instructions
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
        if iteration >= 10:  # Increased limit for report mode, though route_supervisor handles it
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
        
        # Determine next topic
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


def call_researcher_node(state: SupervisorState):
    """Invokes the researcher subgraph with the current research topic."""
    try:
        log_node_state(_state_logger, "call_researcher", "MAIN_GRAPH", dict(state), "BEFORE", state.get("iterations", 0), f"Topic: {state.get('next_topic', 'N/A')}")
        writer = get_stream_writer()
        topic = state["next_topic"]
        
        # Determine breadth based on answer format
        answer_format = state.get("answer_format", "concise")
        breadth = 3 if answer_format == "concise" else 5
        
        node_call_event = create_trace_event("node_call", "call_researcher", {"topic": topic, "breadth": breadth})
        writer({"event": "trace", **node_call_event})
        
        # Track seen URLs to prevent duplicate web_search_url events
        seen_urls = set()
        
        # Stream the subgraph to capture internal events
        final_summary = ""
        
        # stream_mode=["custom", "values"] gives us both events and state updates
        for mode, data in researcher_graph.stream(
            {"topic": topic, "query_breadth": breadth},
            stream_mode=["custom", "values"]
        ):
            print(f"[DEBUG] researcher_graph stream chunk: mode={mode}, type(data)={type(data)}")
            if mode == "custom":
                # Forward custom events (like trace, web_search_url) to main stream
                items = data if isinstance(data, list) else [data]
                for item in items:
                    event_type = item.get('event', 'unknown')
                    print(f"[DEBUG] Forwarding custom event from researcher: {event_type}")
                    
                    # Deduplicate web_search_url events by URL
                    if event_type == "web_search_url":
                        url = item.get("url")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            writer(item)
                        else:
                            print(f"[DEBUG] Skipping duplicate web_search_url: {url}")
                    else:
                        # Forward all other events normally
                        writer(item)
            elif mode == "values":
                # Capture the latest research summary
                if "research_summary" in data:
                    final_summary = data["research_summary"]
        
        formatted_note = f"## Research on: {topic}\n{final_summary}"
        
        result = {"research_notes": [formatted_note], "execution_trace": [node_call_event]}
        log_node_state(_state_logger, "call_researcher", "MAIN_GRAPH", {**state, **result}, "AFTER", state.get("iterations", 0), f"Summary length: {len(final_summary)} chars")
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


# Create main graph using create_agent_graph()
# Lazy initialization to avoid circular import (agent_graph imports from orchestrator)
_main_graph = None

def __getattr__(name: str):
    """Lazy initialization of main_graph to avoid circular imports."""
    global _main_graph
    if name == "main_graph":
        if _main_graph is None:
            from polyplexity_agent.graphs.agent_graph import create_agent_graph
            _main_graph = create_agent_graph(settings, _checkpointer)
        return _main_graph
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

