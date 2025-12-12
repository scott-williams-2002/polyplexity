"""
Factory functions for creating mock response objects.

Provides helper functions to create mock LLM responses, API responses,
and other external service responses for testing.
"""
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

from polyplexity_agent.models import SearchQueries, SupervisorDecision


def create_mock_supervisor_decision(
    next_step: str = "research",
    research_topic: str = "test topic",
    reasoning: str = "Need to research",
    answer_format: str = "concise",
) -> Mock:
    """Create mock SupervisorDecision object.

    Args:
        next_step: "research", "finish", or "clarify".
        research_topic: Topic to research if next_step is "research".
        reasoning: Reasoning for the decision.
        answer_format: "concise" or "report".

    Returns:
        Mock SupervisorDecision instance.
    """
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = next_step
    decision.research_topic = research_topic
    decision.reasoning = reasoning
    decision.answer_format = answer_format
    return decision


def create_mock_search_queries(queries: Optional[List[str]] = None) -> SearchQueries:
    """Create mock SearchQueries response.

    Args:
        queries: List of search queries. Defaults to sample queries.

    Returns:
        SearchQueries instance.
    """
    if queries is None:
        queries = ["AI definition", "AI applications", "AI history"]
    return SearchQueries(queries=queries)


def create_mock_tavily_results(
    num_results: int = 2,
    topic: str = "artificial intelligence",
) -> Dict[str, List[Dict[str, str]]]:
    """Create mock Tavily search results.

    Args:
        num_results: Number of results to generate.
        topic: Topic being searched.

    Returns:
        Dictionary with mock search results.
    """
    results = []
    for i in range(num_results):
        results.append({
            "title": f"{topic.title()} Overview {i+1}",
            "url": f"https://example.com/{topic.replace(' ', '-')}-{i+1}",
            "content": f"{topic.title()} is a branch of computer science... Result {i+1}",
        })
    return {"results": results}


def create_mock_polymarket_results(
    num_markets: int = 2,
    topic: str = "2024 election",
) -> List[Dict[str, Any]]:
    """Create mock Polymarket search results.

    Args:
        num_markets: Number of markets to generate.
        topic: Topic being searched.

    Returns:
        List of mock market dictionaries.
    """
    markets = []
    for i in range(num_markets):
        markets.append({
            "title": f"{topic.title()} Market {i+1}",
            "slug": f"{topic.replace(' ', '-')}-market-{i+1}",
            "description": f"Predictions for {topic} - Market {i+1}",
            "markets": [],
        })
    return markets


def create_mock_market_queries_response(
    queries: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """Create mock market queries response.

    Args:
        queries: List of queries. Defaults to sample queries.

    Returns:
        Dictionary with queries list.
    """
    if queries is None:
        queries = ["2024 election", "presidential race", "election predictions"]
    return {"queries": queries}


def create_mock_market_ranking_response(
    num_markets: int = 1,
) -> Dict[str, List[Dict[str, Any]]]:
    """Create mock market ranking response.

    Args:
        num_markets: Number of ranked markets.

    Returns:
        Dictionary with ranked_markets list.
    """
    ranked_markets = []
    for i in range(num_markets):
        ranked_markets.append({
            "title": f"Ranked Market {i+1}",
            "slug": f"ranked-market-{i+1}",
            "description": f"Description for market {i+1}",
            "markets": [],
        })
    return {"ranked_markets": ranked_markets}


def create_mock_market_evaluation_response(
    decision: str = "APPROVE",
    num_markets: int = 1,
) -> Dict[str, Any]:
    """Create mock market evaluation response.

    Args:
        decision: "APPROVE" or "REJECT".
        num_markets: Number of approved markets.

    Returns:
        Dictionary with decision and markets.
    """
    markets = []
    if decision == "APPROVE":
        for i in range(num_markets):
            markets.append({
                "title": f"Approved Market {i+1}",
                "slug": f"approved-market-{i+1}",
                "description": f"Description for approved market {i+1}",
                "markets": [],
            })
    return {"decision": decision, "markets": markets}


def create_mock_llm_response(content: str = "Mock LLM response") -> Mock:
    """Create mock LLM response object.

    Args:
        content: Response content text.

    Returns:
        Mock LLM response instance.
    """
    response = Mock()
    response.content = content
    return response


def create_mock_llm_chain(
    structured_output: Optional[Any] = None,
    invoke_return: Optional[Any] = None,
) -> Mock:
    """Create mock LLM chain with common patterns.

    Args:
        structured_output: Mock structured output response.
        invoke_return: Mock invoke return value.

    Returns:
        Mock LLM chain instance.
    """
    chain = Mock()
    if structured_output:
        chain.with_structured_output.return_value.with_retry.return_value.invoke.return_value = structured_output
    if invoke_return:
        chain.invoke.return_value = invoke_return
    return chain
