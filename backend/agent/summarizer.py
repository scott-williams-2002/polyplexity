"""
Summarizer module for conversation history management.
Handles summarization of chat context and pruning of raw history.
"""
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from .prompts.system_prompts import SUMMARIZER_SYSTEM_PROMPT
from .utils.helpers import create_llm_model


def manage_chat_history(current: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    Custom reducer for conversation_history.
    1. Checks for reset signal (type="reset") to replace history.
    2. Appends new messages.
    3. Enforces a hard safety limit (e.g., keep last 50).
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
    """
    try:
        history = state.get("conversation_history", [])
        if not history:
            return {}

        current_summary = state.get("conversation_summary", "None")
        history_str = _format_history_for_summary(history)
        new_summary = _generate_summary(current_summary, history_str)

        # Keep only the last message (the assistant's latest response) to maintain immediate context
        # But since we summarized everything, maybe we just keep the last 2 (User + Asst)?
        # The user asked for "summary + only newest interaction".
        # If this node runs after assistant response, "newest" is (User, Asst).
        # So we should probably keep nothing, as the NEXT turn will start with a new User message.
        # So "conversation_history" will be [New User Message] + Summary.
        # So we can clear the history here.
        
        return {
            "conversation_summary": new_summary,
            "conversation_history": [{"type": "reset"}],
        }
    except Exception as e:
        print(f"Error in summarize_conversation_node: {e}")
        raise e

