from pathlib import Path
from typing import Union


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
        print(f"Graph visualization saved to: {absolute_path}")
        return absolute_path
    except Exception as e:
        print(f"Error saving graph visualization: {e}")
        raise

