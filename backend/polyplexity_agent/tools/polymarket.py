"""
Polymarket API interaction tools.

This module provides functions for interacting with the Polymarket API,
including searching for markets, fetching events by tag ID, retrieving
tag batches, and processing market data structures.
"""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from polyplexity_agent.config import Settings

POLYMARKET_SEARCH_URL = "https://gamma-api.polymarket.com/public-search"
POLYMARKET_EVENTS_URL = "https://gamma-api.polymarket.com/events"
POLYMARKET_TAGS_URL = "https://gamma-api.polymarket.com/tags"


def _fetch_search_results(query: str) -> Dict[str, Any]:
    """
    Fetch raw search results from Polymarket API.

    Args:
        query: The search query string.

    Returns:
        A dictionary containing the raw API response with events and markets.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    params = {"q": query}
    response = requests.get(POLYMARKET_SEARCH_URL, params=params)
    response.raise_for_status()
    return response.json()


def _parse_json_field(value: Any, default: Any = None) -> Any:
    """
    Parse a JSON string field, returning default if parsing fails.

    Handles cases where the value may be None, a JSON string, or already
    parsed. Returns the default value if parsing fails or value is None.

    Args:
        value: The value to parse, which may be a JSON string, None, or
            already parsed data.
        default: The default value to return if parsing fails or value is
            None. Defaults to None.

    Returns:
        The parsed JSON data, or the default value if parsing fails.
    """
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    return value


def _extract_market_data(
    market: Dict[str, Any],
    event_title: str = "",
    event_slug: str = "",
    event_image: str = "",
) -> Dict[str, Any]:
    """
    Extract relevant fields from a single market object.

    Processes a raw market dictionary, parsing JSON string fields and
    extracting key market information including clobTokenIds, outcomes,
    and pricing data.

    Args:
        market: The raw market dictionary from the API.
        event_title: The title of the parent event. Defaults to empty string.
        event_slug: The slug of the parent event. Defaults to empty string.
        event_image: The image URL of the parent event. Defaults to empty
            string.

    Returns:
        A dictionary containing extracted and processed market data with
        fields: question, slug, clobTokenIds, description, image,
        conditionId, liquidity, volume, outcomes, outcomePrices,
        eventTitle, eventSlug, eventImage.
    """
    clob_token_ids_raw = market.get("clobTokenIds", "")
    clob_token_ids = _parse_json_field(clob_token_ids_raw, [])

    outcomes_raw = market.get("outcomes", "")
    outcomes = _parse_json_field(outcomes_raw, [])

    outcome_prices_raw = market.get("outcomePrices", "")
    outcome_prices = _parse_json_field(outcome_prices_raw, [])

    image = market.get("image") or market.get("icon") or event_image

    return {
        "question": market.get("question", ""),
        "slug": market.get("slug", ""),
        "clobTokenIds": clob_token_ids,
        "description": market.get("description", ""),
        "image": image,
        "conditionId": market.get("conditionId", ""),
        "liquidity": market.get("liquidity", ""),
        "volume": market.get("volume", ""),
        "outcomes": outcomes,
        "outcomePrices": outcome_prices,
        "eventTitle": event_title,
        "eventSlug": event_slug,
        "eventImage": event_image,
    }


def _process_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a raw event object into a simplified structure.

    Extracts event metadata and processes all associated markets,
    creating a simplified event structure with processed market data.

    Args:
        event: The raw event dictionary from the API.

    Returns:
        A simplified event dictionary containing title, slug, description,
        image, and a list of processed market dictionaries.
    """
    event_title = event.get("title", "")
    event_slug = event.get("slug", "")
    event_image = event.get("image") or event.get("icon", "")

    markets = [
        _extract_market_data(m, event_title, event_slug, event_image)
        for m in event.get("markets", [])
    ]

    return {
        "title": event_title,
        "slug": event_slug,
        "description": event.get("description", ""),
        "image": event_image,
        "markets": markets,
    }

def search_markets(query: str) -> List[Dict[str, Any]]:
    """
    Search Polymarket for events and markets.

    Args:
        query: The search term to query Polymarket.

    Returns:
        A list of simplified event dictionaries, each containing processed
        market data.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    data = _fetch_search_results(query)
    events = data.get("events", [])
    return [_process_event(event) for event in events]


def _fetch_event_details(slug: str) -> List[Dict[str, Any]]:
    """
    Fetch raw event details from Polymarket API by slug.

    Args:
        slug: The event slug identifier.

    Returns:
        A list of raw event dictionaries from the API response.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    params = {"slug": slug}
    response = requests.get(POLYMARKET_EVENTS_URL, params=params)
    response.raise_for_status()
    return response.json()


def get_event_details(slug: str) -> Optional[Dict[str, Any]]:
    """
    Get full details for a specific event by slug.

    Fetches and processes event details, returning a simplified event
    structure with processed market data.

    Args:
        slug: The event slug string identifier.

    Returns:
        A simplified event dictionary with processed markets, or None if
        the event is not found.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    events = _fetch_event_details(slug)
    if not events:
        return None
    return _process_event(events[0])


def _normalize_tag_name(tag_name: str) -> str:
    """
    Normalize tag name for matching.

    Converts tag name to lowercase and strips whitespace to enable
    case-insensitive and spacing-tolerant matching.

    Args:
        tag_name: The tag name to normalize.

    Returns:
        The normalized tag name (lowercase, trimmed).
    """
    return tag_name.lower().strip()


def fetch_tags_batch(offset: int, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch a batch of tags from Polymarket API.

    Retrieves a paginated batch of tags from the Polymarket tags endpoint.
    Used for tag selection in the market research workflow.

    Args:
        offset: Pagination offset for the batch.
        limit: Number of tags to fetch per batch. Defaults to 20.

    Returns:
        A list of tag dictionaries, each containing id, label, and slug
        fields.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    params = {"limit": limit, "offset": offset, "ascending": True}
    response = requests.get(POLYMARKET_TAGS_URL, params=params)
    response.raise_for_status()
    return response.json()


def fetch_events_by_tag_id(tag_id: str) -> List[Dict[str, Any]]:
    """
    Fetch events from Polymarket API filtered by tag ID.

    Retrieves all events associated with a specific tag ID and processes
    them into simplified event structures with market data. Only includes
    events where updatedAt is within the configured lookback period.

    Args:
        tag_id: The tag ID to filter events by.

    Returns:
        A list of simplified event dictionaries, each containing processed
        market data for events matching the tag and within the lookback period.

    Raises:
        requests.HTTPError: If the API request fails.
    """
    settings = Settings()
    lookback_cutoff = datetime.now() - timedelta(days=settings.max_event_lookback_days)
    
    params = {"tag_id": tag_id}
    response = requests.get(POLYMARKET_EVENTS_URL, params=params)
    response.raise_for_status()
    events = response.json()
    
    filtered_events = []
    for event in events:
        updated_at_str = event.get("updatedAt")
        if not updated_at_str:
            continue
        
        try:
            # Parse ISO datetime string (handles formats like "2024-01-15T10:30:00Z" or "2024-01-15T10:30:00.000Z")
            updated_at_str_normalized = updated_at_str.replace("Z", "+00:00")
            updated_at = datetime.fromisoformat(updated_at_str_normalized)
            
            # Convert to naive datetime for comparison (remove timezone info)
            if updated_at.tzinfo:
                updated_at = updated_at.replace(tzinfo=None)
            
            # Only include events where updatedAt >= (now - lookback_days)
            if updated_at >= lookback_cutoff:
                filtered_events.append(event)
        except (ValueError, AttributeError):
            # Skip events with invalid datetime format
            continue
    
    return [_process_event(event) for event in filtered_events]

