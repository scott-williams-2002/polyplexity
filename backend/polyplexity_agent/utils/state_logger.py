"""
State logging utility for LangGraph execution tracking.
Captures full state dumps before and after each node execution.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class StateLogger:
    """Manages state logging to text files for debugging and analysis."""
    
    def __init__(self, log_file_path: Path):
        """
        Initialize the state logger with a log file path.
        
        Args:
            log_file_path: Path to the log file where states will be written
        """
        self.log_file_path = log_file_path
        self.log_file = None
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Ensure the log file exists and is ready for writing."""
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        # Open in append mode to support multiple writes
        self.log_file = open(self.log_file_path, "a", encoding="utf-8")
    
    def _format_state_value(self, value: Any, max_length: int = 2000) -> str:
        """
        Format a state value for readable output.
        Truncates very long values with an indicator.
        
        Args:
            value: The value to format
            max_length: Maximum length before truncation
            
        Returns:
            Formatted string representation
        """
        if value is None:
            return "None"
        
        if isinstance(value, str):
            if len(value) > max_length:
                return f"{value[:max_length]}... [TRUNCATED - {len(value)} total chars]"
            return value
        
        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                return "[]"
            # For lists, show first few items and count
            if len(value) > 5:
                preview = "\n".join([f"  - {self._format_state_value(item, max_length=500)}" 
                                     for item in value[:3]])
                return f"[\n{preview}\n  ... ({len(value) - 3} more items)\n]"
            else:
                items = "\n".join([f"  - {self._format_state_value(item, max_length=500)}" 
                                  for item in value])
                return f"[\n{items}\n]"
        
        if isinstance(value, dict):
            # Format dict with indentation
            formatted_items = []
            for k, v in value.items():
                formatted_items.append(f"  {k}: {self._format_state_value(v, max_length=500)}")
            return "{\n" + "\n".join(formatted_items) + "\n}"
        
        # For other types, use string representation
        str_repr = str(value)
        if len(str_repr) > max_length:
            return f"{str_repr[:max_length]}... [TRUNCATED - {len(str_repr)} total chars]"
        return str_repr
    
    def log_state(
        self,
        node_name: str,
        graph_type: str,
        state: Dict[str, Any],
        timing: str,
        iteration: Optional[int] = None,
        additional_info: Optional[str] = None
    ):
        """
        Log state information to the log file.
        
        Args:
            node_name: Name of the node being executed
            graph_type: Type of graph (MAIN_GRAPH or SUBGRAPH)
            state: The state dictionary to log
            timing: When this log occurs (BEFORE, AFTER, INITIAL, FINAL, etc.)
            iteration: Optional iteration number
            additional_info: Optional additional context information
        """
        if not self.log_file:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Build log entry header
        header_parts = [f"[{timestamp}]", f"{graph_type}", f"{node_name}", f"({timing})"]
        if iteration is not None:
            header_parts.append(f"Iteration: {iteration}")
        
        header = " ".join(header_parts)
        
        # Write header
        self.log_file.write("=" * 80 + "\n")
        self.log_file.write(header + "\n")
        self.log_file.write("=" * 80 + "\n")
        
        # Write additional info if provided
        if additional_info:
            self.log_file.write(f"Additional Info: {additional_info}\n")
            self.log_file.write("-" * 80 + "\n")
        
        # Write formatted state
        self.log_file.write("State:\n")
        for key, value in state.items():
            formatted_value = self._format_state_value(value)
            self.log_file.write(f"{key}:\n{formatted_value}\n")
            self.log_file.write("-" * 80 + "\n")
        
        self.log_file.write("\n")
        self.log_file.flush()  # Ensure it's written immediately
    
    def close(self):
        """Close the log file."""
        if self.log_file:
            self.log_file.close()
            self.log_file = None
