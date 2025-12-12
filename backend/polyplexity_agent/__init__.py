"""
Research agent module.
Exports the main entry point for the multi-agent research system.
"""

__all__ = ["run_research_agent", "main_graph", "_checkpointer"]


def __getattr__(name: str):
    """
    Lazy import of components to avoid importing heavy dependencies
    when only config or other modules are needed.
    
    Args:
        name: Name of the attribute to import
        
    Returns:
        The requested attribute from entrypoint or state_manager module
        
    Raises:
        AttributeError: If the attribute doesn't exist
    """
    if name in __all__:
        if name == "run_research_agent":
            from .entrypoint import run_research_agent
            return run_research_agent
        elif name in ["main_graph", "_checkpointer"]:
            from .utils.state_manager import main_graph, _checkpointer
            return main_graph if name == "main_graph" else _checkpointer
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

