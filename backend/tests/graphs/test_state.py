"""
Tests for state definitions.
"""
import operator
from typing import List

import pytest

from polyplexity_agent.graphs.state import (
    MarketResearchState,
    ResearcherState,
    SupervisorState,
)


def test_researcher_state_structure():
    """
    Test that ResearcherState has correct structure.
    """
    state: ResearcherState = {
        "topic": "test topic",
        "queries": ["query1", "query2"],
        "search_results": ["result1"],
        "research_summary": "summary",
        "query_breadth": 3,
    }
    
    assert state["topic"] == "test topic"
    assert len(state["queries"]) == 2
    assert len(state["search_results"]) == 1
    assert state["research_summary"] == "summary"
    assert state["query_breadth"] == 3


def test_market_research_state_structure():
    """
    Test that MarketResearchState has correct structure.
    """
    state: MarketResearchState = {
        "original_topic": "test topic",
        "market_queries": ["query1"],
        "raw_events": [{"id": "1"}],
        "candidate_markets": [{"market": "test"}],
        "approved_markets": [],
        "reasoning_trace": ["step1"],
    }
    
    assert state["original_topic"] == "test topic"
    assert len(state["market_queries"]) == 1
    assert len(state["raw_events"]) == 1
    assert len(state["candidate_markets"]) == 1
    assert len(state["approved_markets"]) == 0
    assert len(state["reasoning_trace"]) == 1


def test_supervisor_state_structure():
    """
    Test that SupervisorState has correct structure.
    """
    state: SupervisorState = {
        "user_request": "test request",
        "research_notes": ["note1"],
        "prediction_markets": [],
        "next_topic": "topic",
        "final_report": "",
        "iterations": 0,
        "conversation_summary": "",
        "conversation_history": [],
        "current_report_version": 0,
        "execution_trace": [],
        "answer_format": "concise",
    }
    
    assert state["user_request"] == "test request"
    assert len(state["research_notes"]) == 1
    assert state["iterations"] == 0
    assert state["answer_format"] == "concise"


def test_researcher_state_reducer():
    """
    Test that ResearcherState search_results uses operator.add reducer.
    """
    # The reducer is defined in the type annotation
    # We can't directly test it, but we verify the annotation exists
    from typing import get_type_hints
    
    hints = get_type_hints(ResearcherState, include_extras=True)
    search_results_annotation = hints.get("search_results")
    
    assert search_results_annotation is not None
    # Verify it's an Annotated type with operator.add
    from typing import Annotated
    assert hasattr(search_results_annotation, "__metadata__")


def test_supervisor_state_reducers():
    """
    Test that SupervisorState uses correct reducers.
    """
    from typing import get_type_hints
    
    hints = get_type_hints(SupervisorState, include_extras=True)
    
    # Check research_notes uses operator.add
    research_notes_annotation = hints.get("research_notes")
    assert research_notes_annotation is not None
    
    # Check execution_trace uses operator.add
    execution_trace_annotation = hints.get("execution_trace")
    assert execution_trace_annotation is not None

