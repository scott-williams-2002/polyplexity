"""
Perform search node for the researcher subgraph.

Executes a single Tavily search query and formats results.
"""
from typing import Any, Dict

from langchain_tavily import TavilySearch
from langgraph.config import get_stream_writer

from polyplexity_agent.execution_trace import create_trace_event
from polyplexity_agent.utils.helpers import format_search_url_markdown, log_node_state


def _perform_search_tavily(query: str, max_results: int = 2) -> Dict[str, Any]:
    """Execute Tavily search."""
    tool = TavilySearch(max_results=max_results, topic="general")
    return tool.invoke({"query": query})


def _format_search_results(results: Dict[str, Any], query: str) -> str:
    """Format search results as markdown."""
    content = f"--- Results for '{query}' ---\n"
    for r in results.get("results", []):
        title = r.get('title', 'Untitled')
        url = r.get('url', '')
        text_content = r.get('content', '')
        if url:
            content += f"Title: [{title}]({url})\n"
        else:
            content += f"Title: {title}\n"
        content += f"Content: {text_content}\n\n"
    return content


def perform_search_node(state: dict):
    """Executes a single Tavily search query."""
    try:
        query = state["query"]
        # Access state logger from researcher module temporarily (like Phase 4 pattern)
        from polyplexity_agent.graphs.subgraphs.researcher import _state_logger
        log_node_state(_state_logger, "perform_search", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Search query: {query}")
        
        # This node receives a dict from Send(), which includes query_breadth
        # Default to 2 if missing for backward compatibility
        max_results = state.get("query_breadth", 2)
        
        writer = get_stream_writer()
        node_call_event = create_trace_event("node_call", "perform_search", {"query": query, "max_results": max_results})
        search_start_event = create_trace_event("search", "perform_search", {"event": "search_start", "query": query})
        
        writer({"event": "trace", **node_call_event})
        writer({"event": "trace", **search_start_event})
        writer({"event": "search_start", "query": query})
        
        results = _perform_search_tavily(query, max_results=max_results)
        search_results_list = [{"title": r.get('title', 'Untitled'), "url": r.get('url', '')} for r in results.get("results", [])]
        search_results_event = create_trace_event("search", "perform_search", {"results": search_results_list})
        
        writer({"event": "trace", **search_results_event})
        
        # Emit formatted web_search_url events for frontend display
        for res in results.get("results", []):
            url = res.get('url', '')
            if url:
                markdown = format_search_url_markdown(url)
                print(f"[DEBUG] Emitting web_search_url from researcher node: {url}")
                writer({"event": "web_search_url", "url": url, "markdown": markdown})
        
        content = _format_search_results(results, query)
        
        log_node_state(_state_logger, "perform_search", "SUBGRAPH", {**state, "search_results": [content]}, "AFTER", additional_info=f"Found {len(results.get('results', []))} results")
        return {"search_results": [content], "execution_trace": [node_call_event, search_start_event, search_results_event]}
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "perform_search", "error": str(e), "query": query})
        print(f"Error in perform_search_node for query '{query}': {e}")
        raise
