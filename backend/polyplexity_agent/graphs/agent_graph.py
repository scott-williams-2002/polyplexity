"""
Main agent graph construction and compilation.

This module contains the logic for building and compiling the main supervisor
agent graph using LangGraph.
"""
import traceback
from typing import Any, Optional

from langgraph.graph import END, START, StateGraph

from polyplexity_agent.config import Settings
from polyplexity_agent.config.secrets import create_checkpointer
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.orchestrator import (
    call_researcher_node,
    clarification_node,
    direct_answer_node,
    final_report_node,
    route_supervisor,
    supervisor_node,
)
from polyplexity_agent.summarizer import summarize_conversation_node
from polyplexity_agent.testing import draw_graph


def _ensure_checkpointer_setup(checkpointer: Optional[Any]) -> Optional[Any]:
    """
    Ensure checkpointer setup is called once.
    
    Args:
        checkpointer: The checkpointer instance to setup
        
    Returns:
        The checkpointer instance, or None if setup failed
    """
    if checkpointer:
        try:
            if hasattr(checkpointer, "setup"):
                checkpointer.setup()
                print("✓ LangGraph checkpointer setup completed during graph compilation")
            else:
                print("Warning: Checkpointer does not have setup method")
            return checkpointer
        except Exception as e:
            print(f"Error: Failed to setup checkpointer: {e}")
            traceback.print_exc()
            print("Continuing without checkpointing...")
            return None
    return checkpointer


def create_agent_graph(
    settings: Optional[Settings] = None,
    checkpointer: Optional[Any] = None
) -> Any:
    """
    Create and compile the main supervisor agent graph.
    
    Args:
        settings: Optional Settings instance (creates default if None)
        checkpointer: Optional checkpointer instance (creates one if None)
        
    Returns:
        Compiled LangGraph instance
    """
    if settings is None:
        settings = Settings()
    
    if checkpointer is None:
        checkpointer = create_checkpointer()
    
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
    if checkpointer:
        checkpointer = _ensure_checkpointer_setup(checkpointer)
        if checkpointer:
            compiled_graph = builder.compile(checkpointer=checkpointer)
        else:
            compiled_graph = builder.compile()
    else:
        compiled_graph = builder.compile()
    
    # Save graph visualization
    draw_graph(compiled_graph)
    
    return compiled_graph

