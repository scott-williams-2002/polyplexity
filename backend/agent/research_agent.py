"""
Main research agent entry point.
Orchestrates the multi-agent research system with supervisor and researcher subgraph.
"""
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from utils.db_config import create_checkpointer
from utils.state_logger import StateLogger
from .states import SupervisorState
from .supervisor_nodes import (
    supervisor_node,
    call_researcher_node,
    final_report_node,
    set_state_logger as set_supervisor_logger,
)
from .researcher_nodes import set_state_logger as set_researcher_logger

load_dotenv()

# Global logger instance (set during execution)
_state_logger: Optional[StateLogger] = None

# Output directory for state logs (relative to agent directory)
STATE_LOGS_DIR = Path(__file__).parent / "state_logs"


def route_supervisor(state: SupervisorState):
    """
    Routes supervisor decisions to either final_report or call_researcher.
    
    Args:
        state: SupervisorState containing next_topic
        
    Returns:
        "final_report" if next_topic is "FINISH", otherwise "call_researcher"
    """
    if state["next_topic"] == "FINISH":
        return "final_report"
    return "call_researcher"


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
            _checkpointer_setup_done = True
        except Exception as e:
            print(f"Warning: Failed to setup checkpointer: {e}")
            print("Continuing without checkpointing...")
            _checkpointer = None


# Build Main Graph
builder = StateGraph(SupervisorState)
builder.add_node("supervisor", supervisor_node)
builder.add_node("call_researcher", call_researcher_node)
builder.add_node("final_report", final_report_node)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", route_supervisor)
builder.add_edge("call_researcher", "supervisor")  # Loop back!
builder.add_edge("final_report", END)

# Compile graph with checkpointer if available
if _checkpointer:
    ensure_checkpointer_setup()
    if _checkpointer:
        main_graph = builder.compile(checkpointer=_checkpointer)
    else:
        main_graph = builder.compile()
else:
    main_graph = builder.compile()


def run_research_agent(message: str, thread_id: Optional[str] = None):
    """
    Run the multi-agent research system with streaming support.
    
    This function orchestrates the research workflow:
    1. Checks for existing thread state (follow-up vs new question)
    2. Initializes state logger for debugging
    3. Sets up initial state (following operator.add rules)
    4. Streams graph execution events via SSE
    5. Manages state logger lifecycle
    
    Args:
        message: The user's research question/request
        thread_id: Optional thread ID for checkpointing. If None and checkpointing is available,
                   a new thread_id will be generated.
    
    Yields:
        Tuples of (mode, data) from LangGraph stream:
        - mode="custom": Custom events (supervisor_decision, generated_queries, etc.)
        - mode="updates": State updates from nodes
    """
    global _state_logger
    
    # Generate thread_id if not provided and checkpointing is available
    if thread_id is None and _checkpointer:
        thread_id = f"thread_{uuid.uuid4().hex[:12]}"
    
    # Create config with thread_id if checkpointing is available
    config = {}
    if _checkpointer and thread_id:
        config = {"configurable": {"thread_id": thread_id}}
    
    # Initialize state logger with timestamped filename
    # Ensure output directory exists
    STATE_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_question = re.sub(r'[^\w\s-]', '', message)[:50].strip().replace(' ', '_')
    log_filename = f"state_log_{timestamp}_{sanitized_question}.txt"
    log_path = STATE_LOGS_DIR / log_filename
    
    _state_logger = StateLogger(log_path)
    
    # Set logger in node modules
    set_supervisor_logger(_state_logger)
    set_researcher_logger(_state_logger)
    
    # Check if this is a follow-up (existing thread with state)
    is_follow_up = False
    existing_state = None
    if _checkpointer and thread_id:
        try:
            existing_state_snapshot = main_graph.get_state(config)
            if existing_state_snapshot and existing_state_snapshot.values:
                existing_state = existing_state_snapshot.values
                is_follow_up = True
                
                # Reset execution_trace for new question by updating checkpoint
                # We need to clear execution_trace from checkpoint before starting new question
                # Since operator.add will combine [] with persisted values, we explicitly clear it
                try:
                    # Use LangGraph's update_state to clear execution_trace
                    # This ensures execution_trace starts fresh for each question
                    # Note: We need to get the current checkpoint and update it
                    # For now, we'll rely on setting it to [] and the fact that
                    # nodes will add new events, and final_report_node will use
                    # only the events from this question's execution
                    # The key is that we set execution_trace: [] in initial_state,
                    # and LangGraph should use that as the base (not combine with old)
                    # Actually, operator.add DOES combine, so we need a different approach
                    # We'll track question_execution_trace separately and use that
                    pass
                except Exception as e:
                    print(f"Warning: Could not reset execution_trace: {e}")
        except Exception:
            # Thread doesn't exist yet, start fresh
            pass
    
    # Initialize state
    # IMPORTANT: Do NOT include conversation_history or execution_trace in initial_state when using operator.add
    # The nodes will read existing conversation_history from the checkpointer state via state.get()
    # execution_trace is reset to [] for each new question to avoid accumulation across questions
    # We explicitly set execution_trace to [] to override any persisted value from previous questions
    if is_follow_up and existing_state:
        # For follow-ups, start with empty conversation_history and execution_trace
        # Nodes will read existing conversation_history from checkpointer state
        # execution_trace starts fresh for this question (reset to empty list)
        initial_state = {
            "user_request": message,
            "research_notes": [],  # Start empty - will accumulate via operator.add
            "iterations": 0,
            "conversation_history": [],  # Start empty - nodes read from checkpointer
            "current_report_version": existing_state.get("current_report_version", 0),
            "next_topic": "",
            "final_report": "",  # Clear final_report for new question
            "execution_trace": []  # Reset to empty - will accumulate only for this question
        }
    else:
        initial_state = {
            "user_request": message,
            "research_notes": [],
            "iterations": 0,
            "conversation_history": [],
            "current_report_version": 0,
            "next_topic": "",
            "final_report": "",
            "execution_trace": []  # Reset to empty - will accumulate only for this question
        }
    
    # IMPORTANT: When using operator.add, setting execution_trace to [] in initial_state
    # will cause operator.add to combine [] with any persisted value from checkpoint.
    # To truly reset execution_trace for a new question, we need to explicitly update the checkpoint.
    # We'll do this by invoking the graph with a state update that clears execution_trace.
    # However, a simpler approach is to track execution_trace separately and only store it
    # with messages in conversation_history. For now, we'll rely on final_report_node
    # to capture only the events from this question's execution.
    
    # Log initial state
    _state_logger.log_state(
        node_name="START",
        graph_type="MAIN_GRAPH",
        state=initial_state,
        timing="INITIAL",
        additional_info=f"Starting research for: {message}"
    )
    
    # Yield thread_id as custom event before streaming
    if thread_id:
        yield ("custom", {"event": "thread_id", "thread_id": thread_id})
    
    # Track execution_trace events for this question only
    # This allows us to store only events from current question, not accumulated from previous questions
    question_execution_trace: list = []
    question_start_timestamp = int(time.time() * 1000)  # Milliseconds, for filtering events
    
    # Add thread_id to initial_state so nodes can access it for storing messages
    if thread_id:
        initial_state["_thread_id"] = thread_id
    
    # Stream graph execution
    try:
        for mode, data in main_graph.stream(
            initial_state,
            config=config if config else None,
            stream_mode=["custom", "updates"]
        ):
            # Collect trace events from custom events
            if mode == "custom" and isinstance(data, dict):
                # Handle trace events
                if data.get("event") == "trace":
                    # Extract trace event (remove the "event": "trace" wrapper)
                    trace_event = {k: v for k, v in data.items() if k != "event"}
                    # Track for this question only
                    question_execution_trace.append(trace_event)
                    # Yield trace event for frontend
                    yield mode, {"event": "trace", **trace_event}
                
                # Note: We no longer update state here when supervisor_decision is "finish"
                # Instead, we update state in the "updates" stream when we see next_topic="FINISH"
                # This ensures all trace events from supervisor_node have been collected first
            
            # Also collect key state updates as trace events
            if mode == "updates":
                from .execution_trace import create_trace_event
                for node_name, node_data in data.items():
                    if isinstance(node_data, dict):
                        # Collect execution_trace from final_report node updates (these are the final_report trace events)
                        if node_name == "final_report" and "execution_trace" in node_data:
                            # These are the final_report node's trace events (node_call, writing_report, final_report_complete)
                            final_report_trace_events = node_data.get("execution_trace", [])
                            if isinstance(final_report_trace_events, list):
                                # Add final_report trace events to our collection
                                question_execution_trace.extend(final_report_trace_events)
                        
                        # Emit state update trace events for key changes
                        if "research_notes" in node_data:
                            state_event = create_trace_event(
                                "state_update",
                                node_name,
                                {
                                    "update": "research_notes_added",
                                    "count": len(node_data.get("research_notes", []))
                                }
                            )
                            # Track and yield trace event for frontend
                            question_execution_trace.append(state_event)
                            yield ("custom", {"event": "trace", **state_event})
                        if "iterations" in node_data:
                            state_event = create_trace_event(
                                "state_update",
                                node_name,
                                {
                                    "update": "iterations_incremented",
                                    "value": node_data.get("iterations", 0)
                                }
                            )
                            # Track and yield trace event for frontend
                            question_execution_trace.append(state_event)
                            yield ("custom", {"event": "trace", **state_event})
                        
                        # Log state updates from stream
                        if _state_logger:
                            iteration = node_data.get("iterations")
                            _state_logger.log_state(
                                node_name=f"{node_name}_UPDATE",
                                graph_type="MAIN_GRAPH",
                                state=dict(node_data),
                                timing="STREAM_UPDATE",
                                iteration=iteration,
                                additional_info=f"State update from streaming after {node_name} node"
                            )
            
            yield mode, data
        
        # After graph execution completes, ensure execution trace is stored correctly
        # Since update_state during streaming doesn't work, final_report_node may have stored
        # an incomplete trace. We'll update it with the complete trace here.
        if _checkpointer and thread_id:
            try:
                from utils.message_store import (
                    get_thread_messages, 
                    save_execution_trace, 
                    get_message_traces,
                    delete_message_traces
                )
                
                # Get the most recent assistant message for this thread
                messages = get_thread_messages(thread_id)
                if messages:
                    # Find the last assistant message (should be the one we just created)
                    assistant_messages = [m for m in messages if m["role"] == "assistant"]
                    if assistant_messages:
                        latest_assistant = assistant_messages[-1]
                        assistant_message_id = latest_assistant["id"]
                        
                        # Check how many trace events are currently stored
                        existing_traces = get_message_traces(str(assistant_message_id))
                        existing_count = len(existing_traces)
                        expected_count = len(question_execution_trace)
                        
                        print(f"[DEBUG research_agent] After graph completion:")
                        print(f"[DEBUG research_agent] Existing trace events: {existing_count}, Expected: {expected_count}")
                        
                        # If trace is incomplete (only final_report events), replace it with complete trace
                        if existing_count < expected_count:
                            print(f"[DEBUG research_agent] Trace incomplete, updating with complete trace...")
                            
                            # Delete existing traces
                            delete_message_traces(str(assistant_message_id))
                            
                            # Save complete trace
                            for idx, trace_event in enumerate(question_execution_trace):
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
                            
                            print(f"[DEBUG research_agent] Successfully updated trace with {len(question_execution_trace)} events")
                        else:
                            print(f"[DEBUG research_agent] Trace already complete, no update needed")
            except Exception as e:
                print(f"Warning: Failed to update execution trace after graph completion: {e}")
                import traceback
                traceback.print_exc()
        
        # After graph execution completes, ensure messages are stored in table
        # The final_report_node should have already stored them, but we verify here
        # Also attempt to clear execution_trace from state (though update_state with operator.add may not work)
        if _checkpointer and thread_id:
            try:
                # Verify messages were stored (final_report_node should have done this)
                # If not, we can store them here as fallback
                from utils.message_store import get_thread_message_count
                message_count = get_thread_message_count(thread_id)
                
                # Attempt to clear execution_trace using update_state
                # Note: This may not work with operator.add, but we'll try
                try:
                    # Get current state to see if we need to clear execution_trace
                    current_state = main_graph.get_state(config)
                    if current_state and current_state.values:
                        execution_trace_in_state = current_state.values.get("execution_trace", [])
                        # If execution_trace has accumulated from previous questions, try to clear it
                        # However, update_state with operator.add will append, not replace
                        # So we'll document this limitation
                        if len(execution_trace_in_state) > len(question_execution_trace):
                            # Execution trace has accumulated - we can't easily clear it with operator.add
                            # But we've stored the correct trace in the table, so this is okay
                            pass
                except Exception as e:
                    print(f"Warning: Could not check/clear execution_trace: {e}")
            except Exception as e:
                print(f"Warning: Failed to verify message storage: {e}")
    finally:
        # Close logger
        if _state_logger:
            _state_logger.close()
            print(f"\n📝 State log saved to: {log_path.absolute()}")
            _state_logger = None
            set_supervisor_logger(None)
            set_researcher_logger(None)

