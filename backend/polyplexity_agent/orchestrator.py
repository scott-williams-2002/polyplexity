"""
Main orchestrator module.

DEPRECATED: This module is kept temporarily for backward compatibility.
All functionality has been moved to polyplexity_agent.utils.state_manager.

This module re-exports from state_manager to maintain compatibility during migration.
"""
# Re-export all symbols from state_manager for backward compatibility
from polyplexity_agent.utils.state_manager import (
    _checkpointer,
    _state_logger,
    ensure_checkpointer_setup,
    set_state_logger,
)

# Lazy import for main_graph to avoid circular dependencies
def __getattr__(name: str):
    """Lazy initialization of main_graph to avoid circular imports."""
    if name == "main_graph":
        from polyplexity_agent.utils.state_manager import main_graph
        return main_graph
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
