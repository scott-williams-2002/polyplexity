"""
Helper functions for agent operations.
Extracted from node implementations to keep nodes concise and maintainable.
"""
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from polyplexity_agent.config import Settings
from polyplexity_agent.db_utils import get_database_manager

from polyplexity_agent.prompts.thread_prompts import THREAD_NAME_GENERATION_PROMPT_TEMPLATE


# Application settings
_settings = Settings()

# Lightweight model for fast thread name generation
_thread_name_model = ChatGroq(
    model=_settings.thread_name_model,
    temperature=_settings.thread_name_temperature
)


def format_date() -> str:
    """Format current date as 'MM DD YY'."""
    return datetime.now().strftime("%m %d %y")


def create_llm_model(model_name: Optional[str] = None, temperature: Optional[float] = None) -> ChatGroq:
    """
    Create a ChatGroq LLM model instance.
    
    Args:
        model_name: Model identifier (defaults to settings.model_name)
        temperature: Temperature setting (defaults to settings.temperature)
        
    Returns:
        ChatGroq model instance
    """
    if model_name is None:
        model_name = _settings.model_name
    if temperature is None:
        temperature = _settings.temperature
    return ChatGroq(model=model_name, temperature=temperature)


def generate_thread_name(user_query: str) -> str:
    """
    Generate a concise 5-word name for a thread based on the user's query.
    
    Args:
        user_query: The user's initial query/question
        
    Returns:
        A 5-word (or less) thread name
    """
    try:
        prompt = THREAD_NAME_GENERATION_PROMPT_TEMPLATE.format(user_query=user_query)
        response = _thread_name_model.invoke([HumanMessage(content=prompt)])
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
        from polyplexity_agent.logging import get_logger
        logger = get_logger(__name__)
        logger.warning("thread_name_generation_failed", error=str(e))
        words = user_query.split()[:5]
        name = " ".join(words)
        if len(name) > 50:
            name = name[:47] + "..."
        return name or "New Chat"


def log_node_state(
    logger,
    node_name: str,
    graph_type: str,
    state: Dict[str, Any],
    timing: str,
    iteration: Optional[int] = None,
    additional_info: Optional[str] = None
):
    """
    Log node state using the state logger.
    
    Args:
        logger: StateLogger instance (can be None)
        node_name: Name of the node
        graph_type: Type of graph (MAIN_GRAPH or SUBGRAPH)
        state: State dictionary to log
        timing: Timing indicator (BEFORE, AFTER, INITIAL, etc.)
        iteration: Optional iteration number
        additional_info: Optional additional information string
    """
    if logger:
        logger.log_state(
            node_name=node_name,
            graph_type=graph_type,
            state=state,
            timing=timing,
            iteration=iteration,
            additional_info=additional_info
        )


def save_messages_and_trace(
    thread_id: str,
    user_request: str,
    final_report: str,
    execution_trace: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Save user and assistant messages along with execution trace to database.
    
    Args:
        thread_id: Thread ID
        user_request: User's request text
        final_report: Assistant's final report
        execution_trace: List of trace events
        
    Returns:
        Assistant message ID if successful, None otherwise
    """
    try:
        db_manager = get_database_manager()
        
        # Save user message
        user_message_id = db_manager.save_message(
            thread_id=thread_id,
            role="user",
            content=user_request
        )
        
        # Save assistant message
        assistant_message_id = db_manager.save_message(
            thread_id=thread_id,
            role="assistant",
            content=final_report
        )
        
        # Save execution trace events
        for idx, trace_event in enumerate(execution_trace):
            event_type = trace_event.get("type", "custom")
            event_data = trace_event.get("data", {})
            if "node" not in event_data and "node" in trace_event:
                event_data["node"] = trace_event["node"]
            timestamp = trace_event.get("timestamp", int(time.time() * 1000))
            
            db_manager.save_execution_trace(
                message_id=assistant_message_id,
                event_type=event_type,
                event_data=event_data,
                timestamp=timestamp,
                event_index=idx
            )
        
        return assistant_message_id
    except Exception as e:
        from polyplexity_agent.logging import get_logger
        logger = get_logger(__name__)
        logger.warning("save_messages_failed", error=str(e), exc_info=True)
        import traceback
        traceback.print_exc()
        return None


def ensure_trace_completeness(
    thread_id: str,
    expected_trace: List[Dict[str, Any]]
):
    """
    Ensure execution trace is complete after graph execution.
    Replaces incomplete trace with complete trace if needed.
    
    Args:
        thread_id: Thread ID
        expected_trace: Complete trace that should be stored
    """
    try:
        db_manager = get_database_manager()
        
        messages = db_manager.get_thread_messages(thread_id)
        if not messages:
            return
        
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        if not assistant_messages:
            return
        
        latest_assistant = assistant_messages[-1]
        assistant_message_id = latest_assistant["id"]
        
        existing_traces = db_manager.get_message_traces(str(assistant_message_id))
        existing_count = len(existing_traces)
        expected_count = len(expected_trace)
        
        if existing_count < expected_count:
            from polyplexity_agent.logging import get_logger
            logger = get_logger(__name__)
            logger.debug("trace_incomplete", existing_count=existing_count, expected_count=expected_count)
            db_manager.delete_message_traces(str(assistant_message_id))
            
            for idx, trace_event in enumerate(expected_trace):
                event_type = trace_event.get("type", "custom")
                event_data = trace_event.get("data", {})
                if "node" not in event_data and "node" in trace_event:
                    event_data["node"] = trace_event["node"]
                timestamp = trace_event.get("timestamp", int(time.time() * 1000))
                
                db_manager.save_execution_trace(
                    message_id=assistant_message_id,
                    event_type=event_type,
                    event_data=event_data,
                    timestamp=timestamp,
                    event_index=idx
                )
            
            logger.debug("trace_updated", event_count=len(expected_trace))
    except Exception as e:
        from polyplexity_agent.logging import get_logger
        logger = get_logger(__name__)
        logger.warning("ensure_trace_completeness_failed", error=str(e), exc_info=True)
        import traceback
        traceback.print_exc()


def format_search_url_markdown(url: str) -> str:
    """
    Format a URL into a markdown link with a clean display domain.
    
    Args:
        url: The full URL to format (e.g., 'https://www.example.com/path')
        
    Returns:
        Markdown string (e.g., '[example.com](https://www.example.com/path)')
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return f"[{domain}]({url})"
    except Exception:
        # Fallback for invalid URLs
        return f"[{url}]({url})"
