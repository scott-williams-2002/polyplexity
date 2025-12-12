"""
Tests for Polymarket tool functions.

Note: These tests make actual API calls and may require API keys.
"""
import pytest
from pprint import pprint

from polyplexity_agent.tools.polymarket import get_event_details, search_markets


def test_search_markets():
    """
    Test search_markets function.
    
    This test makes an actual API call to search for markets.
    """
    query = "bitcoin"
    print(f"\n--- Testing search_markets with query: '{query}' ---")
    try:
        results = search_markets(query)
        assert results is not None, "search_markets should return a list"
        if results:
            print(f"Found {len(results)} events.")
            # Print first event as sample
            pprint(results[0], depth=2)
            assert "slug" in results[0], "Results should contain 'slug' field"
        else:
            print("No results found.")
    except Exception as e:
        pytest.fail(f"Error in search_markets: {e}")


@pytest.mark.skip(reason="Requires slug from test_search_markets - run manually if needed")
def test_get_event_details():
    """
    Test get_event_details function.
    
    This test is skipped by default as it requires a slug from test_search_markets.
    To run manually, uncomment and provide a slug.
    """
    slug = None  # Would need to be provided from test_search_markets
    if not slug:
        pytest.skip("No slug provided - run test_search_markets first or provide slug manually")
    
    print(f"\n--- Testing get_event_details with slug: '{slug}' ---")
    try:
        details = get_event_details(slug)
        assert details is not None, "get_event_details should return details or None"
        if details:
            print("Successfully retrieved event details.")
            pprint(details, depth=2)
        else:
            print("Event not found.")
    except Exception as e:
        pytest.fail(f"Error in get_event_details: {e}")


if __name__ == "__main__":
    """
    Manual execution mode - run tests sequentially.
    """
    slug = None
    try:
        results = search_markets("bitcoin")
        if results:
            slug = results[0]["slug"]
            print(f"\nFound slug: {slug}")
            details = get_event_details(slug)
            if details:
                print("Successfully retrieved event details.")
                pprint(details, depth=2)
    except Exception as e:
        print(f"Error: {e}")

