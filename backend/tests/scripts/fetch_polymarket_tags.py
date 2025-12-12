"""
Script to fetch all Polymarket tags and map tag names to IDs.

Fetches all tags from Polymarket Gamma API using pagination,
stores them in JSON format, and provides search functionality.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

import requests

TAGS_API_URL = "https://gamma-api.polymarket.com/tags"
LIMIT = 1000


def _fetch_tags_page(offset: int) -> List[Dict]:
    """Fetch a single page of tags."""
    params = {"limit": LIMIT, "offset": offset, "ascending": True}
    response = requests.get(TAGS_API_URL, params=params)
    response.raise_for_status()
    return response.json()


def fetch_all_tags() -> List[Dict]:
    """
    Fetch all tags from Polymarket API using pagination.

    Returns:
        List of tag dictionaries containing id, label, slug, etc.
    """
    all_tags = []
    offset = 0

    while True:
        tags = _fetch_tags_page(offset)
        if not tags:
            break
        all_tags.extend(tags)
        offset += len(tags)
        if len(tags) < LIMIT:
            break

    return all_tags


def save_tags_to_json(tags: List[Dict], output_path: str) -> None:
    """
    Save tags to JSON file mapping tag ID to label.

    Args:
        tags: List of tag dictionaries from API.
        output_path: Path to output JSON file.
    """
    tags_map = {str(tag["id"]): tag.get("label", tag.get("slug", "")) for tag in tags}

    with open(output_path, "w") as f:
        json.dump(tags_map, f, indent=2)


def _build_reverse_map(tags_map: Dict[str, str]) -> Dict[str, str]:
    """Build reverse mapping from label to ID."""
    return {v.lower(): k for k, v in tags_map.items()}


def _find_tag_id_by_substring(tag_name: str, tags_map: Dict[str, str]) -> Optional[str]:
    """Find tag ID by substring matching (case-insensitive)."""
    tag_lower = tag_name.lower()
    for tag_id, tag_label in tags_map.items():
        if tag_lower in tag_label.lower():
            return tag_id
    return None


def search_tag_ids(tag_names: List[str], tags_file: str) -> Dict[str, Optional[str]]:
    """
    Search for tag IDs by tag names with exact and substring matching.

    Args:
        tag_names: List of tag names to search for.
        tags_file: Path to JSON file containing tag mappings.

    Returns:
        Dictionary mapping tag names to tag IDs (None if not found).
    """
    with open(tags_file, "r") as f:
        tags_map = json.load(f)

    reverse_map = _build_reverse_map(tags_map)
    results = {}

    for name in tag_names:
        tag_id = reverse_map.get(name.lower())
        if not tag_id:
            tag_id = _find_tag_id_by_substring(name, tags_map)
        results[name] = tag_id

    return results


def _load_tag_names(tag_names_file: Path) -> List[str]:
    """Load tag names from JSON file."""
    with open(tag_names_file, "r") as f:
        return json.load(f)


def _print_results(results: Dict[str, Optional[str]]) -> None:
    """Print search results."""
    print("\nTag ID mapping results:")
    for tag_name, tag_id in results.items():
        status = tag_id if tag_id else "NOT FOUND"
        print(f"  {tag_name}: {status}")


def main() -> None:
    """Main entry point: fetch tags, save to JSON, and search for IDs."""
    script_dir = Path(__file__).parent
    tags_file = script_dir / "tags.json"
    tag_names_file = script_dir / "tag_names.json"

    print("Fetching all tags from Polymarket API...")
    all_tags = fetch_all_tags()
    print(f"Fetched {len(all_tags)} tags")

    print(f"Saving tags to {tags_file}...")
    save_tags_to_json(all_tags, str(tags_file))
    print("Tags saved successfully")

    if tag_names_file.exists():
        print(f"Loading tag names from {tag_names_file}...")
        tag_names = _load_tag_names(tag_names_file)
        print("Searching for tag IDs...")
        results = search_tag_ids(tag_names, str(tags_file))
        _print_results(results)
    else:
        print(f"{tag_names_file} not found. Create it with a list of tag names to search.")


if __name__ == "__main__":
    main()
