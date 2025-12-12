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
from polyplexity_agent.graphs.nodes.supervisor.call_researcher import call_researcher_node
from polyplexity_agent.graphs.nodes.supervisor.clarification import clarification_node
from polyplexity_agent.graphs.nodes.supervisor.direct_answer import direct_answer_node
from polyplexity_agent.graphs.nodes.supervisor.final_report import final_report_node
from polyplexity_agent.graphs.nodes.supervisor.supervisor import supervisor_node
from polyplexity_agent.graphs.nodes.supervisor.summarize_conversation import summarize_conversation_node
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.testing import draw_graph

logger = get_logger(__name__)


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
    if answer_format == "concise":
        if current_loop >= 1:
            return "final_report"
    else:
        if current_loop >= 5:
            return "final_report"
    return "call_researcher"


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
                logger.info("checkpointer_setup_completed")
            else:
                logger.warning("checkpointer_no_setup_method")
            return checkpointer
        except Exception as e:
            logger.error("checkpointer_setup_failed", error=str(e), exc_info=True)
            traceback.print_exc()
            logger.info("continuing_without_checkpointing")
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

