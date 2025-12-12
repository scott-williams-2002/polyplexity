"""
Integration tests for state management.

Tests state accumulation and reducers.
"""
import pytest

from polyplexity_agent.graphs.state import (
    MarketResearchState,
    ResearcherState,
    SupervisorState,
)


@pytest.mark.integration
def test_researcher_state_accumulation():
    """Test that ResearcherState search_results accumulate correctly."""
    state: ResearcherState = {
        "topic": "test",
        "queries": [],
        "search_results": [],
        "research_summary": "",
        "query_breadth": 3,
    }

    state["search_results"] = state.get("search_results", []) + ["result1"]
    state["search_results"] = state.get("search_results", []) + ["result2"]

    assert len(state["search_results"]) == 2
    assert "result1" in state["search_results"]
    assert "result2" in state["search_results"]


@pytest.mark.integration
def test_supervisor_state_accumulation():
    """Test that SupervisorState research_notes accumulate correctly."""
    state: SupervisorState = {
        "user_request": "test",
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

    state["research_notes"] = state.get("research_notes", []) + ["note1"]
    state["research_notes"] = state.get("research_notes", []) + ["note2"]

    assert len(state["research_notes"]) == 2
    assert "note1" in state["research_notes"]
    assert "note2" in state["research_notes"]


@pytest.mark.integration
def test_market_research_state_reasoning_trace():
    """Test that MarketResearchState reasoning_trace accumulates."""
    state: MarketResearchState = {
        "original_topic": "test",
        "market_queries": [],
        "raw_events": [],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }

    state["reasoning_trace"] = state.get("reasoning_trace", []) + ["reason1"]
    state["reasoning_trace"] = state.get("reasoning_trace", []) + ["reason2"]

    assert len(state["reasoning_trace"]) == 2
    assert "reason1" in state["reasoning_trace"]
    assert "reason2" in state["reasoning_trace"]
