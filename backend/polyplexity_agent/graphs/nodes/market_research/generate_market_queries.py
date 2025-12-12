"""
Generate market queries node for the market research subgraph.

This node selects relevant tags from Polymarket in batches using LLM-based
selection. It fetches tags in batches of 20, uses an LLM to select relevant
tags from each batch, and continues until 10 tags are selected. Selected tags
are streamed as a single event, and tag IDs are returned for use in fetching
markets.
"""
from typing import Dict, List

from langchain_core.messages import HumanMessage

from polyplexity_agent.config import Settings
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.logging import get_logger
from polyplexity_agent.models import SelectedTags
from polyplexity_agent.prompts.market_prompts import TAG_SELECTION_PROMPT
from polyplexity_agent.streaming import stream_custom_event
from polyplexity_agent.tools.polymarket import _normalize_tag_name, fetch_tags_batch
from polyplexity_agent.utils.helpers import create_llm_model

# Application settings
settings = Settings()
logger = get_logger(__name__)

TARGET_TAG_COUNT = 10
BATCH_SIZE = 20


def _format_tag_batch(tags: List[Dict]) -> str:
    """
    Format tag batch for prompt display.

    Converts a list of tag dictionaries into a formatted string suitable
    for display in LLM prompts, showing tag ID and name/label.

    Args:
        tags: List of tag dictionaries containing id, label, and slug fields.

    Returns:
        A formatted string with one tag per line in the format
        "- ID: {id}, Name: {label}".
    """
    return "\n".join(
        [
            f"- ID: {tag['id']}, Name: {tag.get('label', tag.get('slug', ''))}"
            for tag in tags
        ]
    )


def _map_tag_names_to_ids(selected_names: List[str], tag_batch: List[Dict]) -> List[str]:
    """
    Map selected tag names to tag IDs using normalized matching.

    Matches LLM-selected tag names to their corresponding IDs from the
    tag batch using case-insensitive and whitespace-tolerant matching.

    Args:
        selected_names: List of tag names selected by the LLM.
        tag_batch: List of tag dictionaries from the API batch.

    Returns:
        List of tag ID strings corresponding to the selected names.
        Logs a warning for any names that cannot be matched.
    """
    tag_ids = []
    for name in selected_names:
        normalized_name = _normalize_tag_name(name)
        for tag in tag_batch:
            tag_label = tag.get("label", tag.get("slug", ""))
            if normalized_name == _normalize_tag_name(tag_label):
                tag_ids.append(str(tag["id"]))
                break
        else:
            logger.warning(f"Tag name '{name}' not found in batch")
    return tag_ids


def _select_tags_from_batch(
    original_topic: str, ai_response: str, tag_batch: List[Dict]
) -> SelectedTags:
    """
    Select tags from a batch using LLM.

    Uses an LLM with structured output to select relevant tags from a
    batch based on the original research topic and AI response context.

    Args:
        original_topic: The user's original research topic.
        ai_response: Optional AI-generated response providing context for
            tag selection.
        tag_batch: List of tag dictionaries to select from.

    Returns:
        A SelectedTags object containing selected tag names, reasoning,
        and whether to continue searching.
    """
    model = (
        create_llm_model()
        .with_structured_output(SelectedTags)
        .with_retry(stop_after_attempt=settings.max_structured_output_retries)
    )
    tag_batch_str = _format_tag_batch(tag_batch)
    prompt = TAG_SELECTION_PROMPT.format(
        original_topic=original_topic,
        ai_response=ai_response or "No AI response provided.",
        tag_batch=tag_batch_str,
    )
    return model.invoke([HumanMessage(content=prompt)])


def generate_market_queries_node(state: MarketResearchState):
    """
    Select relevant tags from Polymarket in batches until target count is reached.

    Fetches tags from Polymarket in batches, uses LLM to select relevant tags
    from each batch, and continues until TARGET_TAG_COUNT tags are selected.
    Streams all selected tags as a single event and returns tag IDs for
    market fetching.

    Args:
        state: The market research state containing original_topic and
            optional ai_response.

    Returns:
        A dictionary containing:
            - market_queries: List of selected tag ID strings
            - reasoning_trace: List with a summary message

    Raises:
        Exception: If tag selection fails, streams an error event and re-raises.
    """
    try:
        original_topic = state["original_topic"]
        ai_response = state.get("ai_response", "")

        selected_tag_ids = []
        selected_tags = []  # Track tags with both id and name
        offset = 0

        while len(selected_tag_ids) < TARGET_TAG_COUNT:
            tag_batch = fetch_tags_batch(offset, BATCH_SIZE)
            if not tag_batch:
                break

            response = _select_tags_from_batch(original_topic, ai_response, tag_batch)

            # Map selected names to full tag info (id + name)
            for selected_name in response.selected_tag_names:
                normalized_name = _normalize_tag_name(selected_name)
                for tag in tag_batch:
                    tag_label = tag.get("label", tag.get("slug", ""))
                    if normalized_name == _normalize_tag_name(tag_label):
                        tag_id = str(tag["id"])
                        if tag_id not in selected_tag_ids:
                            selected_tag_ids.append(tag_id)
                            selected_tags.append({"id": tag_id, "name": tag_label})
                            if len(selected_tag_ids) >= TARGET_TAG_COUNT:
                                break
                        break

            if not response.continue_search or len(selected_tag_ids) >= TARGET_TAG_COUNT:
                break

            offset += BATCH_SIZE

        # Stream all selected tags as a single event
        stream_custom_event("tag_selected", "generate_market_queries", {"tags": selected_tags})

        return {
            "market_queries": selected_tag_ids,
            "reasoning_trace": [f"Selected {len(selected_tag_ids)} tags from Polymarket."],
        }
    except Exception as e:
        stream_custom_event("error", "generate_market_queries", {"error": str(e)})
        logger.error("generate_market_queries_node_error", error=str(e), exc_info=True)
        raise
