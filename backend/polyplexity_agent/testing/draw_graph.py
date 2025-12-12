from pathlib import Path
from typing import Union

from polyplexity_agent.logging import get_logger

logger = get_logger(__name__)


def draw_graph(graph, output_path: Union[str, Path] = "graph_visualization.png"):
    """
    Save a LangGraph graph visualization as a PNG image.
    
    Args:
        graph: A compiled LangGraph graph instance
        output_path: Path where to save the PNG file (default: "graph_visualization.png")
    
    Returns:
        Path: The absolute path to the saved file
    
    Raises:
        Exception: If the graph visualization cannot be generated or saved
    """
    try:
        # Get the graph visualization as PNG bytes
        png_bytes = graph.get_graph().draw_mermaid_png()
        
        # Convert to Path object if string
        output_path = Path(output_path)
        
        # Save to file
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        
        absolute_path = output_path.absolute()
        logger.info("graph_visualization_saved", path=str(absolute_path))
        return absolute_path
    except Exception as e:
        logger.error("graph_visualization_save_failed", error=str(e), exc_info=True)
        raise

