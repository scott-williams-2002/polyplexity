"""
Shared pytest fixtures for all tests.

This module provides reusable fixtures for mocking external dependencies,
creating sample states, and setting up test environments.
"""
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.config import Settings
from polyplexity_agent.graphs.state import (
    MarketResearchState,
    ResearcherState,
    SupervisorState,
)
from polyplexity_agent.models import SearchQueries, SupervisorDecision


@pytest.fixture
def mock_settings() -> Settings:
    """Create Settings instance with temporary directory for state logs.

    Returns:
        Settings instance configured for testing.
    """
    settings = Settings()
    settings.state_logs_dir = Path(tempfile.mkdtemp())
    return settings


@pytest.fixture
def mock_llm() -> Iterator[Mock]:
    """Mock LLM instance with common response patterns.

    Yields:
        Mock LLM instance configured for testing.
    """
    mock_llm_instance = Mock()

    supervisor_decision = Mock(spec=SupervisorDecision)
    supervisor_decision.next_step = "research"
    supervisor_decision.research_topic = "test topic"
    supervisor_decision.reasoning = "Need to research"
    supervisor_decision.answer_format = "concise"

    mock_llm_instance.with_structured_output.return_value.with_retry.return_value.invoke.return_value = supervisor_decision
    mock_llm_instance.invoke.return_value.content = "Mock LLM response"

    with patch("polyplexity_agent.utils.helpers.create_llm_model", return_value=mock_llm_instance):
        yield mock_llm_instance


@pytest.fixture
def mock_supervisor_decision_research() -> Mock:
    """Create mock SupervisorDecision for research path.

    Returns:
        Mock SupervisorDecision configured for research.
    """
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "research"
    decision.research_topic = "test topic"
    decision.reasoning = "Need to research"
    decision.answer_format = "concise"
    return decision


@pytest.fixture
def mock_supervisor_decision_finish() -> Mock:
    """Create mock SupervisorDecision for finish path.

    Returns:
        Mock SupervisorDecision configured to finish.
    """
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "finish"
    decision.research_topic = ""
    decision.reasoning = "Have enough information"
    decision.answer_format = "concise"
    return decision


@pytest.fixture
def mock_supervisor_decision_clarify() -> Mock:
    """Create mock SupervisorDecision for clarification path.

    Returns:
        Mock SupervisorDecision configured to clarify.
    """
    decision = Mock(spec=SupervisorDecision)
    decision.next_step = "clarify"
    decision.research_topic = ""
    decision.reasoning = "What location are you interested in?"
    decision.answer_format = "concise"
    return decision


@pytest.fixture
def sample_supervisor_state() -> SupervisorState:
    """Create complete SupervisorState sample.

    Returns:
        Sample SupervisorState dictionary.
    """
    return {
        "user_request": "What is the weather?",
        "research_notes": [],
        "iterations": 0,
        "conversation_history": [],
        "conversation_summary": "",
        "current_report_version": 0,
        "next_topic": "",
        "final_report": "",
        "execution_trace": [],
        "answer_format": "concise",
    }


@pytest.fixture
def sample_supervisor_state_follow_up() -> SupervisorState:
    """Create SupervisorState for follow-up conversation.

    Returns:
        SupervisorState with existing conversation context.
    """
    return {
        "user_request": "Tell me more",
        "research_notes": [],
        "iterations": 0,
        "conversation_history": [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is..."},
        ],
        "conversation_summary": "Previous conversation about AI",
        "current_report_version": 1,
        "next_topic": "",
        "final_report": "",
        "execution_trace": [],
        "answer_format": "concise",
    }


@pytest.fixture
def sample_researcher_state() -> ResearcherState:
    """Create complete ResearcherState sample.

    Returns:
        Sample ResearcherState dictionary.
    """
    return {
        "topic": "artificial intelligence",
        "queries": [],
        "search_results": [],
        "research_summary": "",
        "query_breadth": 3,
    }


@pytest.fixture
def sample_market_research_state() -> MarketResearchState:
    """Create complete MarketResearchState sample.

    Returns:
        Sample MarketResearchState dictionary.
    """
    return {
        "original_topic": "2024 US presidential election",
        "market_queries": [],
        "raw_events": [],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }


@pytest.fixture
def mock_checkpointer() -> Mock:
    """Create mock checkpointer for thread persistence tests.

    Returns:
        Mock checkpointer instance.
    """
    checkpointer = Mock()
    checkpointer.get_state.return_value = None
    return checkpointer


@pytest.fixture
def mock_state_logger() -> Mock:
    """Create mock StateLogger instance.

    Returns:
        Mock StateLogger instance.
    """
    logger = Mock()
    logger.close = Mock()
    logger.log = Mock()
    return logger


@pytest.fixture
def mock_researcher_graph() -> Iterator[Mock]:
    """Mock researcher subgraph with stream method.

    Yields:
        Mock researcher graph instance.
    """
    def mock_stream(input_state: Dict[str, Any], stream_mode: List[str]) -> Iterator[tuple]:
        """Mock researcher graph stream."""
        yield ("custom", [{"event": "web_search_url", "url": "https://example.com"}])
        yield ("values", {"research_summary": "Mock research summary about the topic"})

    with patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.researcher_graph") as mock_researcher:
        mock_researcher.stream = mock_stream
        mock_researcher.invoke = Mock(return_value={"research_summary": "Mock research summary"})
        yield mock_researcher


@pytest.fixture
def mock_market_research_graph() -> Iterator[Mock]:
    """Mock market research subgraph with stream method.

    Yields:
        Mock market research graph instance.
    """
    def mock_stream(input_state: Dict[str, Any], stream_mode: List[str]) -> Iterator[tuple]:
        """Mock market research graph stream."""
        yield ("custom", {"event": "market_search", "query": "test query"})
        yield ("values", {"approved_markets": [{"slug": "test-market"}]})

    with patch("polyplexity_agent.graphs.nodes.supervisor.call_researcher.market_research_graph") as mock_graph:
        mock_graph.stream = mock_stream
        mock_graph.invoke = Mock(return_value={"approved_markets": [{"slug": "test-market"}]})
        yield mock_graph


@pytest.fixture
def mock_graph() -> Iterator[Mock]:
    """Create mock main agent graph with stream method.

    Yields:
        Mock agent graph instance.
    """
    graph = Mock()
    graph.stream = Mock()
    graph.get_state = Mock(return_value=None)
    graph.invoke = Mock()

    with patch("polyplexity_agent.entrypoint.create_default_graph", return_value=graph):
        yield graph


@pytest.fixture
def mock_tavily_search() -> Iterator[Mock]:
    """Mock TavilySearch tool.

    Yields:
        Mock TavilySearch tool instance.
    """
    mock_tool = Mock()
    mock_tool.invoke.return_value = {
        "results": [
            {
                "title": "AI Overview",
                "url": "https://example.com/ai",
                "content": "Artificial intelligence is a branch of computer science...",
            },
            {
                "title": "Machine Learning Basics",
                "url": "https://example.com/ml",
                "content": "Machine learning is a subset of AI...",
            },
        ]
    }

    with patch("polyplexity_agent.graphs.nodes.researcher.perform_search.TavilySearch", return_value=mock_tool):
        yield mock_tool


@pytest.fixture
def mock_polymarket_search() -> Iterator[Mock]:
    """Mock Polymarket search function.

    Yields:
        Mock search_markets function.
    """
    mock_results = [
        {
            "title": "2024 Presidential Election",
            "slug": "2024-presidential-election",
            "description": "Who will win the 2024 US presidential election?",
            "markets": [],
        },
        {
            "title": "Election Predictions",
            "slug": "election-predictions",
            "description": "Predictions for the 2024 election",
            "markets": [],
        },
    ]

    with patch("polyplexity_agent.graphs.nodes.market_research.fetch_markets.search_markets", return_value=mock_results):
        yield mock_results


@pytest.fixture
def mock_database() -> Mock:
    """Mock database connection/manager.

    Returns:
        Mock database instance.
    """
    db = Mock()
    db.execute = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def mock_search_queries() -> SearchQueries:
    """Create mock SearchQueries response.

    Returns:
        SearchQueries instance with sample queries.
    """
    return SearchQueries(queries=["AI definition", "AI applications", "AI history"])


@pytest.fixture
def mock_tavily_results() -> Dict[str, List[Dict[str, str]]]:
    """Create mock Tavily search results.

    Returns:
        Dictionary with mock search results.
    """
    return {
        "results": [
            {
                "title": "AI Overview",
                "url": "https://example.com/ai",
                "content": "Artificial intelligence is a branch of computer science...",
            },
            {
                "title": "Machine Learning Basics",
                "url": "https://example.com/ml",
                "content": "Machine learning is a subset of AI...",
            },
        ]
    }


@pytest.fixture
def mock_polymarket_results() -> List[Dict[str, Any]]:
    """Create mock Polymarket search results.

    Returns:
        List of mock market dictionaries.
    """
    return [
        {
            "title": "2024 Presidential Election",
            "slug": "2024-presidential-election",
            "description": "Who will win the 2024 US presidential election?",
            "markets": [],
        },
        {
            "title": "Election Predictions",
            "slug": "election-predictions",
            "description": "Predictions for the 2024 election",
            "markets": [],
        },
    ]


@pytest.fixture
def mock_queries_response() -> Dict[str, List[str]]:
    """Create mock market queries response.

    Returns:
        Dictionary with queries list.
    """
    return {"queries": ["2024 election", "presidential race", "election predictions"]}


@pytest.fixture
def mock_ranking_response() -> Dict[str, List[Dict[str, Any]]]:
    """Create mock market ranking response.

    Returns:
        Dictionary with ranked_markets list.
    """
    return {
        "ranked_markets": [
            {
                "title": "2024 Presidential Election",
                "slug": "2024-presidential-election",
                "description": "Who will win?",
                "markets": [],
            },
        ]
    }


@pytest.fixture
def mock_evaluation_response() -> Dict[str, Any]:
    """Create mock market evaluation response.

    Returns:
        Dictionary with decision and markets.
    """
    return {
        "decision": "APPROVE",
        "markets": [
            {
                "title": "2024 Presidential Election",
                "slug": "2024-presidential-election",
                "description": "Who will win?",
                "markets": [],
            },
        ],
    }
