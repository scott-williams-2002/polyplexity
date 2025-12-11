import requests
from typing import List, Dict, Any, Optional

POLYMARKET_SEARCH_URL = "https://gamma-api.polymarket.com/public-search"
POLYMARKET_EVENTS_URL = "https://gamma-api.polymarket.com/events"

def _fetch_search_results(query: str) -> Dict[str, Any]:
    """Fetch raw search results from Polymarket API."""
    params = {"q": query}
    response = requests.get(POLYMARKET_SEARCH_URL, params=params)
    response.raise_for_status()
    return response.json()

def _extract_market_data(market: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant fields from a single market object."""
    return {
        "question": market.get("question", ""),
        "slug": market.get("slug", ""),
        "clobTokenIds": market.get("clobTokenIds", []),
        "description": market.get("description", ""),
        "outcomes": market.get("outcomes", []),
        "outcomePrices": market.get("outcomePrices", [])
    }

def _process_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process a raw event object into a simplified structure."""
    return {
        "title": event.get("title", ""),
        "slug": event.get("slug", ""),
        "description": event.get("description", ""),
        "markets": [_extract_market_data(m) for m in event.get("markets", [])]
    }

def search_markets(query: str) -> List[Dict[str, Any]]:
    """
    Search Polymarket for events and markets.
    
    Args:
        query: The search term.
        
    Returns:
        List of simplified event dictionaries.
    """
    data = _fetch_search_results(query)
    events = data.get("events", [])
    return [_process_event(event) for event in events]

def _fetch_event_details(slug: str) -> List[Dict[str, Any]]:
    """Fetch raw event details from Polymarket API by slug."""
    params = {"slug": slug}
    response = requests.get(POLYMARKET_EVENTS_URL, params=params)
    response.raise_for_status()
    return response.json()

def get_event_details(slug: str) -> Optional[Dict[str, Any]]:
    """
    Get full details for a specific event by slug.
    
    Args:
        slug: The event slug string.
        
    Returns:
        Simplified event dictionary or None if not found.
    """
    events = _fetch_event_details(slug)
    if not events:
        return None
    return _process_event(events[0])

