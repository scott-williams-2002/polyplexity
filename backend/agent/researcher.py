"""
Researcher subgraph implementation.
Handles focused research workflow: Topic -> Generate Queries -> Parallel Search -> Synthesize Results
"""
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .execution_trace import create_trace_event
from .models import SearchQueries
from .prompts import (
    QUERY_GENERATION_SYSTEM_PROMPT,
    QUERY_GENERATION_USER_PROMPT_TEMPLATE,
)
from .prompts.research_prompts import RESEARCH_SYNTHESIS_PROMPT_TEMPLATE
from .states import ResearcherState
from .utils.helpers import create_llm_model, format_date, log_node_state, format_search_url_markdown

# Global state logger instance
_state_logger: Optional[object] = None

# Model configuration
configurable_model = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
max_structured_output_retries = 3


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


# Helper functions for node logic
def _generate_queries_llm(state: ResearcherState) -> SearchQueries:
    """Generate search queries using LLM."""
    model = create_llm_model().with_structured_output(SearchQueries).with_retry(stop_after_attempt=max_structured_output_retries)
    system_prompt = QUERY_GENERATION_SYSTEM_PROMPT
    user_prompt = QUERY_GENERATION_USER_PROMPT_TEMPLATE.format(
        current_date=format_date(),
        topic=state['topic']
    )
    return model.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])


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


def _synthesize_research_llm(state: ResearcherState) -> str:
    """Synthesize research results using LLM."""
    raw_data = "\n".join(state["search_results"])
    prompt = RESEARCH_SYNTHESIS_PROMPT_TEMPLATE.format(
        current_date=format_date(),
        topic=state['topic'],
        raw_data=raw_data
    )
    response = create_llm_model().invoke([HumanMessage(content=prompt)])
    return response.content


# Node implementations (each ≤15 lines)
def generate_queries_node(state: ResearcherState):
    """Breaks a research topic into distinct search queries."""
    try:
        log_node_state(_state_logger, "generate_queries", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Topic: {state.get('topic', 'N/A')}")
        writer = get_stream_writer()
        writer({"event": "researcher_thinking", "topic": state['topic']})
        
        resp = _generate_queries_llm(state)
        node_call_event = create_trace_event("node_call", "generate_queries", {})
        queries_event = create_trace_event("custom", "generate_queries", {"event": "generated_queries", "queries": resp.queries})
        
        writer({"event": "trace", **node_call_event})
        writer({"event": "trace", **queries_event})
        writer({"event": "generated_queries", "queries": resp.queries})
        
        log_node_state(_state_logger, "generate_queries", "SUBGRAPH", {**state, "queries": resp.queries}, "AFTER", additional_info=f"Generated {len(resp.queries)} queries")
        return {"queries": resp.queries, "execution_trace": [node_call_event, queries_event]}
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "generate_queries", "error": str(e)})
        print(f"Error in generate_queries_node: {e}")
        raise


def perform_search_node(state: dict):
    """Executes a single Tavily search query."""
    try:
        query = state["query"]
        log_node_state(_state_logger, "perform_search", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Search query: {query}")
        
        # This node receives a dict from Send(), which might not have query_breadth
        # But wait, Send() only sends what we give it.
        # We need to update map_queries to pass query_breadth if it's not in 'state' (which is just the payload)
        # However, 'state' here IS the payload.
        # So map_queries needs to send it.
        
        # But wait, perform_search_node input is the state of the *node*, which is just the payload from Send.
        # It's not the full ResearcherState.
        
        # Let's check if query_breadth is in the payload. It should be if we update map_queries.
        # For now, default to 2 if missing.
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


def synthesize_research_node(state: ResearcherState):
    """Summarizes all search results into a clean research note."""
    try:
        log_node_state(_state_logger, "synthesize_research", "SUBGRAPH", dict(state), "BEFORE", additional_info=f"Search results count: {len(state.get('search_results', []))}")
        
        writer = get_stream_writer()
        node_call_event = create_trace_event("node_call", "synthesize_research", {})
        synthesis_event = create_trace_event("custom", "synthesize_research", {"event": "research_synthesis_done"})
        
        writer({"event": "trace", **node_call_event})
        writer({"event": "trace", **synthesis_event})
        
        summary = _synthesize_research_llm(state)
        writer({"event": "research_synthesis_done", "summary": summary[:100] + "..."})
        
        log_node_state(_state_logger, "synthesize_research", "SUBGRAPH", {**state, "research_summary": summary}, "AFTER", additional_info=f"Research summary length: {len(summary)} chars")
        return {"research_summary": summary, "execution_trace": [node_call_event, synthesis_event]}
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "synthesize_research", "error": str(e)})
        print(f"Error in synthesize_research_node: {e}")
        raise


def map_queries(state: ResearcherState):
    """Maps queries to parallel search node invocations."""
    breadth = state.get("query_breadth", 2)
    return [Send("perform_search", {"query": q, "query_breadth": breadth}) for q in state["queries"]]


def build_researcher_subgraph():
    """Build and compile the researcher subgraph."""
    builder = StateGraph(ResearcherState)
    builder.add_node("generate_queries", generate_queries_node)
    builder.add_node("perform_search", perform_search_node)
    builder.add_node("synthesize_research", synthesize_research_node)
    
    builder.add_edge(START, "generate_queries")
    builder.add_conditional_edges("generate_queries", map_queries, ["perform_search"])
    builder.add_edge("perform_search", "synthesize_research")
    builder.add_edge("synthesize_research", END)
    
    return builder.compile()


# Compile the subgraph at module level
researcher_graph = build_researcher_subgraph()

