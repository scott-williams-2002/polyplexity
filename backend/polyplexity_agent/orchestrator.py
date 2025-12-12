"""
Main orchestrator module.

Temporarily maintains global state logger and checkpointer instances.
These will be refactored in later phases.
"""
import traceback
from typing import Optional

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


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


# Create checkpointer if database is configured
_checkpointer = create_checkpointer()
_checkpointer_setup_done = False


def ensure_checkpointer_setup():
    """Ensure checkpointer setup is called once."""
    global _checkpointer_setup_done, _checkpointer
    if _checkpointer and not _checkpointer_setup_done:
        try:
            if hasattr(_checkpointer, "setup"):
                _checkpointer.setup()
                logger.info("checkpointer_setup_completed")
            else:
                logger.warning("checkpointer_no_setup_method")
            _checkpointer_setup_done = True
        except Exception as e:
            logger.error("checkpointer_setup_failed", error=str(e), exc_info=True)
            traceback.print_exc()
            logger.info("continuing_without_checkpointing")
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
