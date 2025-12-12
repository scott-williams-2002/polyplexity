"""
State manager module for global application state.

Manages global state logger, checkpointer, and main graph instances.
This module centralizes state management that was previously in orchestrator.py.
"""
import traceback
from typing import Any, Optional

from dotenv import load_dotenv

from polyplexity_agent.config import Settings
from polyplexity_agent.config.secrets import create_checkpointer
from polyplexity_agent.logging import get_logger
from polyplexity_agent.utils.state_logger import StateLogger

load_dotenv()

# Application settings
settings = Settings()
logger = get_logger(__name__)

# Global logger instance
_state_logger: Optional[StateLogger] = None


def set_state_logger(logger_instance: Optional[StateLogger]) -> None:
    """
    Set the global state logger instance.
    
    Args:
        logger_instance: The StateLogger instance to set, or None to clear
    """
    global _state_logger
    _state_logger = logger_instance


# Create checkpointer if database is configured
_checkpointer = create_checkpointer()
_checkpointer_setup_done = False


def ensure_checkpointer_setup(checkpointer: Optional[Any] = None) -> Optional[Any]:
    """
    Ensure checkpointer setup is called once.
    
    Args:
        checkpointer: Optional checkpointer instance. If None, uses global _checkpointer.
        
    Returns:
        The checkpointer instance, or None if setup failed or checkpointer is None
    """
    global _checkpointer_setup_done, _checkpointer
    
    # Use provided checkpointer or global one
    target_checkpointer = checkpointer if checkpointer is not None else _checkpointer
    
    if target_checkpointer and not _checkpointer_setup_done:
        try:
            if hasattr(target_checkpointer, "setup"):
                target_checkpointer.setup()
                logger.info("checkpointer_setup_completed")
            else:
                logger.warning("checkpointer_no_setup_method")
            _checkpointer_setup_done = True
            return target_checkpointer
        except Exception as e:
            logger.error("checkpointer_setup_failed", error=str(e), exc_info=True)
            traceback.print_exc()
            logger.info("continuing_without_checkpointing")
            _checkpointer_setup_done = True  # Mark as done to prevent retrying
            if checkpointer is None:
                _checkpointer = None
            return None
    
    return target_checkpointer


# Create main graph using create_agent_graph()
# Lazy initialization to avoid circular import
_main_graph: Optional[Any] = None


def __getattr__(name: str) -> Any:
    """
    Lazy initialization of main_graph to avoid circular imports.
    
    Args:
        name: Name of the attribute to get
        
    Returns:
        The requested attribute (main_graph)
        
    Raises:
        AttributeError: If the attribute doesn't exist
    """
    global _main_graph
    if name == "main_graph":
        if _main_graph is None:
            from polyplexity_agent.graphs.agent_graph import create_agent_graph
            _main_graph = create_agent_graph(settings, _checkpointer)
        return _main_graph
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# Export all public symbols
__all__ = [
    "_state_logger",
    "_checkpointer",
    "set_state_logger",
    "ensure_checkpointer_setup",
    "main_graph",  # Accessed via __getattr__
]
