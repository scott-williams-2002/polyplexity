"""
Researcher subgraph node implementations.
These nodes handle the research workflow: Topic -> Queries -> Parallel Search -> Synthesis.
"""
from datetime import datetime
from typing import Optional

from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.config import get_stream_writer

from .models import SearchQueries
from .states import ResearcherState
from .prompts import (
    QUERY_GENERATION_SYSTEM_PROMPT,
    QUERY_GENERATION_USER_PROMPT_TEMPLATE,
)
from .execution_trace import create_trace_event

# Global state logger instance (set during execution)
_state_logger: Optional[object] = None

# Model configuration
configurable_model = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
max_structured_output_retries = 3


def set_state_logger(logger):
    """Set the global state logger instance."""
    global _state_logger
    _state_logger = logger


def generate_queries_node(state: ResearcherState):
    """
    Breaks a research topic into distinct search queries.
    
    Uses structured output to generate 3-6 distinct queries that cover
    different angles of the research topic.
    
    Args:
        state: ResearcherState containing the topic to research
        
    Returns:
        Dictionary with 'queries' key containing list of search queries
    """
    # Log state BEFORE node execution
    if _state_logger:
        _state_logger.log_state(
            node_name="generate_queries",
            graph_type="SUBGRAPH",
            state=dict(state),
            timing="BEFORE",
            additional_info=f"Topic: {state.get('topic', 'N/A')}"
        )
    
    try:
        writer = get_stream_writer()
        writer({"event": "researcher_thinking", "topic": state['topic']})
        
        # Configure model for structured query generation with retries
        research_model = (
            configurable_model
            .with_structured_output(SearchQueries)
            .with_retry(stop_after_attempt=max_structured_output_retries)
        )
        
        current_date = datetime.now().strftime("%m %d %y")
        system_prompt = QUERY_GENERATION_SYSTEM_PROMPT
        user_prompt = QUERY_GENERATION_USER_PROMPT_TEMPLATE.format(
            current_date=current_date,
            topic=state['topic']
        )
        
        # Use structured output with explicit JSON instructions in prompts
        resp = research_model.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        # Create and emit node call trace event
        node_call_event = create_trace_event("node_call", "generate_queries", {})
        writer({"event": "trace", **node_call_event})
        
        # Create and emit generated queries trace event
        queries_event = create_trace_event(
            "custom",
            "generate_queries",
            {
                "event": "generated_queries",
                "queries": resp.queries
            }
        )
        writer({"event": "trace", **queries_event})
        writer({"event": "generated_queries", "queries": resp.queries})
        
        # Use node_call_event and queries_event created earlier
        result = {
            "queries": resp.queries,
            "execution_trace": [node_call_event, queries_event]
        }
        
        # Log state AFTER node execution
        if _state_logger:
            updated_state = {**state, **result}
            _state_logger.log_state(
                node_name="generate_queries",
                graph_type="SUBGRAPH",
                state=dict(updated_state),
                timing="AFTER",
                additional_info=f"Generated {len(resp.queries)} queries"
            )
        
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "generate_queries", "error": str(e)})
        print(f"Error in generate_queries_node: {e}")
        # Re-raise to let LangGraph handle checkpointing
        raise


def perform_search_node(state: dict):
    """
    Executes a single Tavily search query.
    
    This is a Map step that runs in parallel for multiple queries.
    Formats search results with markdown links and returns them.
    
    Args:
        state: Dictionary containing 'query' key with the search query
        
    Returns:
        Dictionary with 'search_results' key containing formatted search results
    """
    # Note: State here is just the input passed via Send (the query)
    query = state["query"]
    
    # Log state BEFORE node execution
    if _state_logger:
        _state_logger.log_state(
            node_name="perform_search",
            graph_type="SUBGRAPH",
            state=dict(state),
            timing="BEFORE",
            additional_info=f"Search query: {query}"
        )
    
    try:
        writer = get_stream_writer()
        
        # Create and emit node call trace event
        node_call_event = create_trace_event("node_call", "perform_search", {"query": query})
        writer({"event": "trace", **node_call_event})
        
        # Emit search start trace event
        search_start_event = create_trace_event(
            "search",
            "perform_search",
            {"event": "search_start", "query": query}
        )
        writer({"event": "trace", **search_start_event})
        writer({"event": "search_start", "query": query})
        
        tool = TavilySearch(max_results=2, topic="general")
        results = tool.invoke({"query": query})
        
        # Extract titles and URLs for trace
        search_results_list = []
        for r in results.get("results", []):
            title = r.get('title', 'Untitled')
            url = r.get('url', '')
            search_results_list.append({"title": title, "url": url})
        
        # Emit search results trace event
        search_results_event = create_trace_event(
            "search",
            "perform_search",
            {"results": search_results_list}
        )
        writer({"event": "trace", **search_results_event})
        
        # Format results - TavilySearch returns dict with 'results' key
        # Preserve title, url, and content with markdown link formatting
        content = f"--- Results for '{query}' ---\n"
        for r in results.get("results", []):
            title = r.get('title', 'Untitled')
            url = r.get('url', '')
            text_content = r.get('content', '')
            
            # Format as markdown with link: [title](url)
            if url:
                content += f"Title: [{title}]({url})\n"
            else:
                content += f"Title: {title}\n"
            content += f"Content: {text_content}\n\n"
        
        # Use node_call_event, search_start_event, and search_results_event created earlier
        result = {
            "search_results": [content],
            "execution_trace": [node_call_event, search_start_event, search_results_event]
        }
        
        # Log state AFTER node execution
        if _state_logger:
            # Note: In the subgraph context, we might not have full ResearcherState
            # So we log what we have
            updated_state = {**state, **result}
            _state_logger.log_state(
                node_name="perform_search",
                graph_type="SUBGRAPH",
                state=dict(updated_state),
                timing="AFTER",
                additional_info=f"Found {len(results.get('results', []))} results, content length: {len(content)} chars"
            )
        
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "perform_search", "error": str(e), "query": query})
        print(f"Error in perform_search_node for query '{query}': {e}")
        raise


def synthesize_research_node(state: ResearcherState):
    """
    Summarizes all search results into a clean research note.
    
    Takes all accumulated search results and synthesizes them into a
    coherent summary, preserving markdown links from sources.
    
    Args:
        state: ResearcherState containing search_results and topic
        
    Returns:
        Dictionary with 'research_summary' key containing synthesized summary
    """
    # Log state BEFORE node execution
    if _state_logger:
        search_results_count = len(state.get("search_results", []))
        total_search_content_length = sum(len(str(r)) for r in state.get("search_results", []))
        _state_logger.log_state(
            node_name="synthesize_research",
            graph_type="SUBGRAPH",
            state=dict(state),
            timing="BEFORE",
            additional_info=f"Search results count: {search_results_count}, Total content length: {total_search_content_length} chars"
        )
    
    try:
        writer = get_stream_writer()
        
        # Create and emit node call trace event
        node_call_event = create_trace_event("node_call", "synthesize_research", {})
        writer({"event": "trace", **node_call_event})
        
        # Create and emit synthesis done trace event
        synthesis_event = create_trace_event(
            "custom",
            "synthesize_research",
            {"event": "research_synthesis_done"}
        )
        writer({"event": "trace", **synthesis_event})
        
        # Simple synthesis prompt with link preservation instructions
        raw_data = "\n".join(state["search_results"])
        current_date = datetime.now().strftime("%m %d %y")
        prompt = (
            f"For context, the current date is {current_date}.\n\n"
            f"Analyze the following search results about '{state['topic']}'. "
            "Write a detailed summary of the findings. Ignore irrelevant info.\n\n"
            "IMPORTANT: Maintain inline links with facts using markdown format: [link text](url). "
            "When citing information from sources, preserve the source URLs inline with the facts. "
            "Format links as markdown: [descriptive text](source_url).\n\n"
            f"{raw_data}"
        )
        response = configurable_model.invoke([HumanMessage(content=prompt)])
        
        writer({"event": "research_synthesis_done", "summary": response.content[:100] + "..."})
        
        # Use node_call_event and synthesis_event created earlier
        result = {
            "research_summary": response.content,
            "execution_trace": [node_call_event, synthesis_event]
        }
        
        # Log state AFTER node execution
        if _state_logger:
            updated_state = {**state, **result}
            _state_logger.log_state(
                node_name="synthesize_research",
                graph_type="SUBGRAPH",
                state=dict(updated_state),
                timing="AFTER",
                additional_info=f"Research summary length: {len(response.content)} chars"
            )
        
        return result
    except Exception as e:
        writer = get_stream_writer()
        writer({"event": "error", "node": "synthesize_research", "error": str(e)})
        print(f"Error in synthesize_research_node: {e}")
        raise

