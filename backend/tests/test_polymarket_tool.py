import sys
import os
from pprint import pprint

from polyplexity_agent.tools.polymarket import search_markets, get_event_details

def test_search_markets():
    query = "bitcoin"
    print(f"\n--- Testing search_markets with query: '{query}' ---")
    try:
        results = search_markets(query)
        if not results:
            print("No results found.")
        else:
            print(f"Found {len(results)} events.")
            # Print first event as sample
            pprint(results[0], depth=2)
            
            # Use the first result's slug for the next test
            return results[0]["slug"]
    except Exception as e:
        print(f"Error in search_markets: {e}")
        return None

def test_get_event_details(slug):
    if not slug:
        print("\nSkipping test_get_event_details (no slug provided)")
        return

    print(f"\n--- Testing get_event_details with slug: '{slug}' ---")
    try:
        details = get_event_details(slug)
        if details:
            print("Successfully retrieved event details.")
            pprint(details, depth=2)
        else:
            print("Event not found.")
    except Exception as e:
        print(f"Error in get_event_details: {e}")

if __name__ == "__main__":
    slug = test_search_markets()
    test_get_event_details(slug)

