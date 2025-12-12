"""
Summarize conversation node for the main agent graph.

Summarizes conversation history and prunes the raw history.
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from polyplexity_agent.logging import get_logger
from polyplexity_agent.prompts.system_prompts import SUMMARIZER_SYSTEM_PROMPT
from polyplexity_agent.utils.helpers import create_llm_model

logger = get_logger(__name__)


def manage_chat_history(current: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    Custom reducer for conversation_history.
    
    1. Checks for reset signal (type="reset") to replace history.
    2. Appends new messages.
    3. Enforces a hard safety limit (e.g., keep last 50).
    
    Args:
        current: Current conversation history list
        new: New messages to add
        
    Returns:
        Updated conversation history list
    """
    if new and isinstance(new, list) and len(new) > 0:
        if new[0].get("type") == "reset":
            return new[1:]
    full_list = current + new
    if len(full_list) > 50:
        return full_list[-50:]
    return full_list


def _format_history_for_summary(history: List[Dict]) -> str:
    """Formats conversation history for the summarizer prompt."""
    formatted = []
    for msg in history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted.append(f"{role.upper()}: {content}")
    return "\n".join(formatted)


def _generate_summary(current_summary: str, history_str: str) -> str:
    """Generates the updated summary using the LLM."""
    prompt = f"Current Summary:\n{current_summary}\n\nRecent History:\n{history_str}"
    messages = [
        SystemMessage(content=SUMMARIZER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    response = create_llm_model().invoke(messages)
    return response.content


def summarize_conversation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarizes conversation history and prunes the raw history.
    
    Args:
        state: The current state dictionary
        
    Returns:
        Updated state dictionary with conversation_summary and pruned history
    """
    try:
        history = state.get("conversation_history", [])
        if not history:
            return {}
        current_summary = state.get("conversation_summary", "None")
        history_str = _format_history_for_summary(history)
        new_summary = _generate_summary(current_summary, history_str)
        return {
            "conversation_summary": new_summary,
            "conversation_history": [{"type": "reset"}],
        }
    except Exception as e:
        logger.error("summarize_conversation_node_error", error=str(e), exc_info=True)
        raise e
