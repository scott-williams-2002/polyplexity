"""
Test fixtures and sample data for market research e2e tests.
"""
from typing import Dict, List

from polyplexity_agent.graphs.state import MarketResearchState


def create_sample_market_research_state(topic: str = "2024 US presidential election") -> MarketResearchState:
    """
    Create a sample MarketResearchState for testing.
    
    Args:
        topic: Research topic string
        
    Returns:
        Sample MarketResearchState dictionary
    """
    return {
        "original_topic": topic,
        "market_queries": [],
        "raw_events": [],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }


def create_sample_market_queries() -> List[str]:
    """
    Create sample market queries for testing.
    
    Returns:
        List of sample query strings
    """
    return [
        "2024 election",
        "presidential race",
        "election predictions",
    ]


def create_sample_raw_events() -> List[Dict]:
    """
    Create sample raw event data from Polymarket API.
    
    Returns:
        List of sample event dictionaries
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
