"""
Supervisor graph node implementations.
These nodes orchestrate the research workflow: Assess -> Delegate -> Assess -> Write Report.
"""
import time
from datetime import datetime
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.config import get_stream_writer

from .models import SupervisorDecision
from .states import SupervisorState
from .research_subgraph import researcher_graph
from .prompts import (
    SUPERVISOR_SYSTEM_PROMPT_TEMPLATE,
    SUPERVISOR_FOLLOW_UP_SYSTEM_PROMPT_TEMPLATE,
    SUPERVISOR_USER_PROMPT_TEMPLATE,
    SUPERVISOR_FOLLOW_UP_CONTEXT_TEMPLATE,
)
from .execution_trace import create_trace_event

# Global state logger instance (set during execution)
_state_logger: Optional[object] = None

# Model configuration
configurable_model = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
max_structured_output_retries = 3

# Lightweight model for fast thread name generation
thread_name_model = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


def generate_thread_name(user_query: str) -> str:
    """
    Generate a concise 5-word name for a thread based on the user's query.
    
    Uses a lightweight LLM call to create a descriptive name. Falls back to
    a simple truncation if the LLM call fails.
    
    Args:
        user_query: The user's initial query/question
        
    Returns:
        A 5-word (or less) thread name
    """
    try:
        # Use lightweight model for fast generation
        prompt = (
            f"Create a concise thread title (exactly 5 words or less) for this user query: {user_query}\n\n"
            "Respond with ONLY the title, no explanation or quotes."
        )
        
        response = thread_name_model.invoke([HumanMessage(content=prompt)])
        name = response.content.strip()
        
        # Remove quotes if present
        if name.startswith('"') and name.endswith('"'):
            name = name[1:-1]
        if name.startswith("'") and name.endswith("'"):
            name = name[1:-1]
        
        # Ensure it's 5 words or less
        words = name.split()
        if len(words) > 5:
            name = " ".join(words[:5])
        
        # Fallback to truncated query if name is empty or too short
        if not name or len(name) < 3:
            words = user_query.split()[:5]
            name = " ".join(words)
            if len(name) > 50:
                name = name[:47] + "..."
        
        return name
    except Exception as e:
        # Fallback: use first 5 words of query
        print(f"Warning: Failed to generate thread name: {e}")
        words = user_query.split()[:5]
        name = " ".join(words)
        if len(name) > 50:
            name = name[:47] + "..."
        return name or "New Chat"


def supervisor_node(state: SupervisorState):
    """
    Decides whether to research more or finish and write the final report.
    
    Uses structured output to make a decision about whether more research
    is needed or if enough information has been gathered to answer the user's request.
    
    Args:
        state: SupervisorState containing user_request, research_notes, etc.
        
    Returns:
        Dictionary with 'next_topic' key (research topic or "FINISH")
    """
    # Log state BEFORE node execution
    if _state_logger:
        iteration = state.get("iterations", 0)
        _state_logger.log_state(
            node_name="supervisor",
            graph_type="MAIN_GRAPH",
            state=dict(state),
            timing="BEFORE",
            iteration=iteration
        )
    
    try:
        writer = get_stream_writer()
        iteration = state.get("iterations", 0)
        
        # Generate and emit thread name for new threads (first iteration)
        if iteration == 0:
            try:
                thread_id = state.get("_thread_id")
                user_request = state.get("user_request", "")
                
                if thread_id and user_request:
                    # Generate thread name
                    thread_name = generate_thread_name(user_request)
                    
                    # Store thread name in database
                    try:
                        from utils.message_store import save_thread_name
                        save_thread_name(thread_id, thread_name)
                    except Exception as e:
                        print(f"Warning: Failed to save thread name: {e}")
                    
                    # Emit thread name event for frontend
                    writer({
                        "event": "thread_name",
                        "thread_id": thread_id,
                        "name": thread_name
                    })
            except Exception as e:
                print(f"Warning: Failed to generate thread name: {e}")
        
        # Create and emit node call trace event
        node_call_event = create_trace_event("node_call", "supervisor", {})
        writer({"event": "trace", **node_call_event})
        
        # Hard limit to prevent infinite loops
        if iteration >= 5:
            writer({"event": "supervisor_log", "message": "Max iterations reached. Forcing finish."})
            result = {
                "next_topic": "FINISH",
                "execution_trace": [node_call_event]
            }
            # Log state AFTER node execution
            if _state_logger:
                updated_state = {**state, **result}
                _state_logger.log_state(
                    node_name="supervisor",
                    graph_type="MAIN_GRAPH",
                    state=dict(updated_state),
                    timing="AFTER",
                    iteration=iteration,
                    additional_info="Max iterations reached"
                )
            return result

        notes_context = "\n\n".join(state.get("research_notes", []))
        current_date = datetime.now().strftime("%m %d %y")
        
        # Check if this is a follow-up question (has existing report or conversation history)
        is_follow_up = bool(state.get("final_report") or state.get("conversation_history"))
        existing_report = state.get("final_report", "")
        conversation_history = state.get("conversation_history", [])
        
        # Configure model for structured supervisor decision with retries
        supervisor_model = (
            configurable_model
            .with_structured_output(SupervisorDecision)
            .with_retry(stop_after_attempt=max_structured_output_retries)
        )
        
        # Build system message using templates
        if is_follow_up:
            system_msg = SUPERVISOR_FOLLOW_UP_SYSTEM_PROMPT_TEMPLATE.format(
                current_date=current_date
            )
        else:
            system_msg = SUPERVISOR_SYSTEM_PROMPT_TEMPLATE.format(
                current_date=current_date
            )
        
        # Build user message with follow-up context if needed
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
            iteration=iteration,
            notes_context=notes_context
        )
        
        # Get structured decision using tool calling
        decision = supervisor_model.invoke(
            [SystemMessage(content=system_msg), HumanMessage(content=user_msg)]
        )
        
        # Emit reasoning trace event
        reasoning_event = create_trace_event(
            "reasoning",
            "supervisor",
            {"reasoning": decision.reasoning}
        )
        writer({"event": "trace", **reasoning_event})
        
        # Emit supervisor decision event (custom event)
        decision_event = create_trace_event(
            "custom",
            "supervisor",
            {
                "event": "supervisor_decision",
                "decision": decision.next_step,
                "reasoning": decision.reasoning,
                "topic": decision.research_topic
            }
        )
        writer({"event": "trace", **decision_event})
        
        # Also emit original event for backward compatibility
        writer({
            "event": "supervisor_decision", 
            "decision": decision.next_step, 
            "reasoning": decision.reasoning,
            "topic": decision.research_topic
        })

        # Use node_call_event created earlier (at line 66)
        if decision.next_step == "finish":
            result = {
                "next_topic": "FINISH",
                "execution_trace": [node_call_event, reasoning_event, decision_event]
            }
        else:
            result = {
                "next_topic": decision.research_topic,
                "iterations": iteration + 1,
                "execution_trace": [node_call_event, reasoning_event, decision_event]
            }
        
        # Log state AFTER node execution
        if _state_logger:
            updated_state = {**state, **result}
            _state_logger.log_state(
                node_name="supervisor",
                graph_type="MAIN_GRAPH",
                state=dict(updated_state),
                timing="AFTER",
                iteration=iteration,
                additional_info=f"Decision: {decision.next_step}, Reasoning: {decision.reasoning}"
            )
        
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "supervisor", "error": str(e)})
        print(f"Error in supervisor_node: {e}")
        raise


def call_researcher_node(state: SupervisorState):
    """
    Acts as the bridge between supervisor and researcher subgraph.
    
    Invokes the compiled researcher subgraph with the topic from state,
    then formats the result as a research note and adds it to the state.
    
    Args:
        state: SupervisorState containing next_topic to research
        
    Returns:
        Dictionary with 'research_notes' key containing formatted research note
    """
    # Log state BEFORE node execution
    if _state_logger:
        iteration = state.get("iterations", 0)
        _state_logger.log_state(
            node_name="call_researcher",
            graph_type="MAIN_GRAPH",
            state=dict(state),
            timing="BEFORE",
            iteration=iteration,
            additional_info=f"About to invoke subgraph with topic: {state.get('next_topic', 'N/A')}"
        )
    
    try:
        writer = get_stream_writer()
        topic = state["next_topic"]
        
        # Create and emit node call trace event
        node_call_event = create_trace_event("node_call", "call_researcher", {"topic": topic})
        writer({"event": "trace", **node_call_event})
        
        # Invoke the subgraph
        # We pass the input state expected by the subgraph
        subgraph_output = researcher_graph.invoke({"topic": topic})
        
        # Extract the result
        summary = subgraph_output["research_summary"]
        
        formatted_note = f"## Research on: {topic}\n{summary}"
        
        # Use node_call_event created earlier
        result = {
            "research_notes": [formatted_note],
            "execution_trace": [node_call_event]
        }
        
        # Log state AFTER node execution
        if _state_logger:
            iteration = state.get("iterations", 0)
            updated_state = {**state, **result}
            _state_logger.log_state(
                node_name="call_researcher",
                graph_type="MAIN_GRAPH",
                state=dict(updated_state),
                timing="AFTER",
                iteration=iteration,
                additional_info=f"Subgraph completed. Research summary length: {len(summary)} chars"
            )
        
        # Return updates to the Supervisor state
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "call_researcher", "error": str(e), "topic": state.get("next_topic", "N/A")})
        print(f"Error in call_researcher_node: {e}")
        raise


def final_report_node(state: SupervisorState):
    """
    Writes the final answer/report based on accumulated research notes.
    
    Synthesizes all research notes into a comprehensive answer to the user's request.
    Handles both new reports and refinements of existing reports for follow-up questions.
    
    Args:
        state: SupervisorState containing research_notes and user_request
        
    Returns:
        Dictionary with 'final_report' and 'current_report_version' keys
    """
    # Log state BEFORE node execution
    if _state_logger:
        iteration = state.get("iterations", 0)
        _state_logger.log_state(
            node_name="final_report",
            graph_type="MAIN_GRAPH",
            state=dict(state),
            timing="BEFORE",
            iteration=iteration,
            additional_info=f"Research notes count: {len(state.get('research_notes', []))}"
        )
    
    try:
        writer = get_stream_writer()
        
        # Create and emit node call trace event
        node_call_event = create_trace_event("node_call", "final_report", {})
        writer({"event": "trace", **node_call_event})
        
        # Create and emit writing report event
        writing_event = create_trace_event(
            "custom",
            "final_report",
            {"event": "writing_report"}
        )
        writer({"event": "trace", **writing_event})
        writer({"event": "writing_report"})
        
        notes = "\n\n".join(state["research_notes"])
        current_date = datetime.now().strftime("%m %d %y")
        
        # Check if this is a follow-up (refining existing report)
        existing_report = state.get("final_report", "")
        current_version = state.get("current_report_version", 0)
        is_refinement = bool(existing_report)
        
        if is_refinement:
            prompt = (
                f"For context, the current date is {current_date}.\n\n"
                f"This is a REFINEMENT of an existing report (Version {current_version}). "
                f"The user has asked a follow-up question: {state['user_request']}\n\n"
                f"Previous Report (Version {current_version}):\n{existing_report}\n\n"
                f"New Research Notes:\n{notes}\n\n"
                "TASK: Refine and expand the existing report based on:\n"
                "- The new research notes provided above\n"
                "- The user's follow-up question\n"
                "- Integrate new findings with existing content\n"
                "- Preserve valuable information from the previous report\n"
                "- Update sections that need correction or expansion\n\n"
                "FORMATTING REQUIREMENTS:\n"
                "- Write the refined answer in markdown format with proper headers, lists, and formatting\n"
                "- Include inline links with facts using markdown format: [fact or description](source_url)\n"
                "- Ensure all cited information includes source URLs inline with the facts\n"
                "- Use proper markdown syntax: headers (# ## ###), lists (- or *), bold (**text**), etc.\n"
                "- Preserve all source links from both old and new research notes\n"
                "- Clearly indicate what's new vs. what was already covered\n"
            )
        else:
            prompt = (
                f"For context, the current date is {current_date}.\n\n"
                f"Based on the following research notes, write a comprehensive answer to: {state['user_request']}\n\n"
                "FORMATTING REQUIREMENTS:\n"
                "- Write the answer in markdown format with proper headers, lists, and formatting\n"
                "- Include inline links with facts using markdown format: [fact or description](source_url)\n"
                "- Ensure all cited information includes source URLs inline with the facts\n"
                "- Use proper markdown syntax: headers (# ## ###), lists (- or *), bold (**text**), etc.\n"
                "- Preserve all source links from the research notes\n\n"
                f"Notes:\n{notes}"
            )
    
        response = configurable_model.invoke([HumanMessage(content=prompt)])
        final_report = response.content
        
        # Emit final report complete trace event
        complete_event = create_trace_event(
            "custom",
            "final_report",
            {
                "event": "final_report_complete",
                "report": final_report
            }
        )
        writer({"event": "trace", **complete_event})
        writer({"event": "final_report_complete", "report": final_report})
        
        # Get thread_id from config to store messages in separate table
        # Use _question_execution_trace which contains only events from the current question
        # This is set by research_agent.py when supervisor decides "finish"
        
        # Get current question's execution trace from state (set by research_agent.py)
        # Note: update_state during streaming doesn't work, so this will likely be empty
        # The complete trace will be stored after graph completion in research_agent.py
        current_question_trace = state.get("_question_execution_trace", [])
        
        # Append final report trace events to current question's trace
        # If current_question_trace is empty (which it will be), this will only contain final_report events
        # research_agent.py will replace this with the complete trace after graph completion
        full_execution_trace = current_question_trace + [node_call_event, writing_event, complete_event]
        
        # Store messages and execution trace in separate Postgres tables
        # This ensures UI-friendly retrieval and proper separation from LangGraph state
        try:
            from utils.message_store import save_message, save_execution_trace
            
            # Get thread_id from config (passed via state metadata or we need to get it differently)
            # For now, we'll store messages but thread_id needs to be available
            # We'll handle this in research_agent.py after graph execution
            # Store messages here if thread_id is available in state
            thread_id = state.get("_thread_id")  # Will be set by research_agent.py
            
            if thread_id:
                # Save user message
                user_message_id = save_message(
                    thread_id=thread_id,
                    role="user",
                    content=state["user_request"]
                )
                
                # Save assistant message
                assistant_message_id = save_message(
                    thread_id=thread_id,
                    role="assistant",
                    content=final_report
                )
                
                # Save execution trace events for assistant message
                for idx, trace_event in enumerate(full_execution_trace):
                    # Extract event data from trace event structure
                    event_type = trace_event.get("type", "custom")
                    event_data = trace_event.get("data", {})
                    # Ensure node is in event_data
                    if "node" not in event_data and "node" in trace_event:
                        event_data["node"] = trace_event["node"]
                    timestamp = trace_event.get("timestamp", int(time.time() * 1000))
                    
                    save_execution_trace(
                        message_id=assistant_message_id,
                        event_type=event_type,
                        event_data=event_data,
                        timestamp=timestamp,
                        event_index=idx
                    )
        except Exception as e:
            # Log error but don't fail - state will still be updated
            print(f"Warning: Failed to save messages to table: {e}")
            import traceback
            traceback.print_exc()
        
        # Still append to conversation_history in state for agent context
        # UI will use separate table, but agent may need this for follow-up context
        user_message = {
            "role": "user",
            "content": state["user_request"],
            "execution_trace": None
        }
        assistant_message = {
            "role": "assistant",
            "content": final_report,
            "execution_trace": full_execution_trace if full_execution_trace else None
        }
        
        # Return state updates including new messages and final report trace events
        # execution_trace in result will be added via operator.add to state
        # conversation_history in result will be added via operator.add to state
        result = {
            "final_report": final_report,
            "current_report_version": current_version + 1,
            "execution_trace": [node_call_event, writing_event, complete_event],
            "conversation_history": [user_message, assistant_message]
        }
        
        # Log state AFTER node execution
        if _state_logger:
            iteration = state.get("iterations", 0)
            updated_state = {**state, **result}
            _state_logger.log_state(
                node_name="final_report",
                graph_type="MAIN_GRAPH",
                state=dict(updated_state),
                timing="AFTER",
                iteration=iteration,
                additional_info=f"Final report length: {len(final_report)} chars"
            )
        
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "final_report", "error": str(e)})
        print(f"Error in final_report_node: {e}")
        raise

