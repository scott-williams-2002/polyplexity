# Tag-Based Market Fetching Implementation

## Overview

This document summarizes the refactoring of the market research subgraph from keyword-based search to tag-based market fetching. The implementation replaces keyword queries with Polymarket tag selection, enabling more precise and relevant market discovery through structured tag categorization.

## Key Changes

### 1. Tag-Based Market Discovery

**Problem**: Keyword-based searches (`/public-search`) were less precise and could miss relevant markets that are properly categorized by tags in Polymarket.

**Solution**: 
- Fetch Polymarket tags in batches of 20
- Use LLM to select relevant tag names from each batch
- Deterministically map tag names to tag IDs
- Fetch events/markets using tag IDs via `/events?tag_id=X` endpoint
- Accumulate up to 10 tags before proceeding to market fetching

**Benefits**:
- More precise market discovery through structured categorization
- Better alignment with Polymarket's tag system
- Reduced API calls by using tag-based filtering
- Maintains backward compatibility for tangential thinking (still uses keywords)

### 2. Incremental Streaming Events

**Problem**: Final results were only available at the end, making it difficult for the frontend to show progress and update UI incrementally.

**Solution**:
- Stream `tag_selected` event after all tags are selected (single event with all tags)
- Stream `market_approved` events incrementally as each market is evaluated
- Stream `market_research_complete` event with final reasoning only
- Removed intermediate logging and trace events to reduce noise

**Event Flow**:
1. `tag_selected` - Contains all selected tags with IDs and names
2. `market_approved` (multiple) - One event per approved market with slug, clobTokenIds, question, description, rules
3. `market_research_complete` - Final event with reasoning summary

**Files Modified**:
- `polyplexity_agent/graphs/nodes/market_research/generate_market_queries.py` - Streams `tag_selected` event
- `polyplexity_agent/graphs/nodes/market_research/evaluate_markets.py` - Streams `market_approved` and `market_research_complete` events
- `polyplexity/docs/STREAM_RULES.md` - Updated with new event definitions

### 3. Code Cleanup and Documentation

**Problem**: Code lacked comprehensive docstrings, imports were not properly organized, and some inline imports existed.

**Solution**:
- Added comprehensive Google-style docstrings to all functions with Args/Returns sections
- Organized imports properly (standard library → third-party → local)
- Moved all inline imports to the top of files
- Improved code formatting and spacing
- Renamed `think_tangentially.py` to `generate_tangential_queries.py` for clarity

**Files Modified**:
- `polyplexity_agent/graphs/subgraphs/market_research.py` - Added docstrings, organized imports
- `polyplexity_agent/tools/polymarket.py` - Added module docstring, improved function docstrings, organized imports
- `polyplexity_agent/graphs/nodes/market_research/generate_market_queries.py` - Added docstrings, organized imports
- `polyplexity_agent/graphs/nodes/market_research/fetch_markets.py` - Added docstrings
- `polyplexity_agent/graphs/nodes/market_research/process_and_rank_markets.py` - Added docstrings, organized imports
- `polyplexity_agent/graphs/nodes/market_research/evaluate_markets.py` - Added docstrings, organized imports
- `polyplexity_agent/graphs/nodes/market_research/think_tangentially.py` → `generate_tangential_queries.py` - Renamed and updated

## Implementation Details

### Tag Selection Workflow

1. **Fetch Tag Batches**: 
   - Start with offset 0, fetch 20 tags per batch
   - Continue until 10 tags selected or no more tags available

2. **LLM Selection**:
   - Present batch to LLM with user topic and AI response context
   - LLM selects tag names (must match exactly from batch)
   - LLM indicates if more batches needed via `continue_search` flag

3. **Tag Name to ID Mapping**:
   - Normalize tag names (lowercase, strip whitespace) for matching
   - Map selected names to tag IDs from batch
   - Accumulate unique tag IDs until 10 reached

4. **Market Fetching**:
   - For each tag ID, fetch events via `/events?tag_id={tag_id}`
   - Extract markets from events
   - Deduplicate by market slug

### State Changes

**Added to `MarketResearchState`**:
- `ai_response: Optional[str]` - AI-generated report providing context for tag selection

**Maintained**:
- `market_queries: List[str]` - Now contains tag IDs (numeric strings) instead of keywords
- Backward compatibility: Non-numeric strings treated as keywords (for tangential thinking)

### New Functions and Models

**Added to `polymarket.py`**:
- `fetch_tags_batch(offset: int, limit: int = 20) -> List[Dict[str, Any]]` - Fetch paginated tags
- `fetch_events_by_tag_id(tag_id: str) -> List[Dict[str, Any]]` - Fetch events by tag ID
- `_normalize_tag_name(tag_name: str) -> str` - Normalize tag names for matching

**Added to `models.py`**:
- `SelectedTags` - Structured output for tag selection:
  - `selected_tag_names: List[str]` - Tag names selected from batch
  - `reasoning: str` - Why these tags were selected
  - `continue_search: bool` - Whether to fetch more batches

**Added to `market_prompts.py`**:
- `TAG_SELECTION_PROMPT` - Prompt for LLM tag selection with context from user topic and AI response

### Streaming Events

**New Events**:
- `tag_selected` - Emitted after all tags are selected
  - Payload: `{"tags": [{"id": str, "name": str}, ...]}`
  - Node: `generate_market_queries`

- `market_approved` - Emitted incrementally for each approved market
  - Payload: `{"slug": str, "clobTokenIds": List[str], "question": str, "description": str, "rules": str}`
  - Node: `evaluate_markets`

- `market_research_complete` - Final event with reasoning
  - Payload: `{"reasoning": str}`
  - Node: `evaluate_markets`

**Removed Events**:
- Intermediate `node_call` trace events
- Intermediate `execution_trace` events
- Logging events (`log_node_state` calls)

## Test Updates

### Updated Test Files

All test files were updated to match the new implementation:

1. **test_generate_market_queries.py**:
   - Updated to test tag selection instead of keyword generation
   - Mocks `fetch_tags_batch` instead of LLM query generation
   - Tests `tag_selected` event streaming
   - Removed `execution_trace` and `log_node_state` assertions

2. **test_fetch_markets.py**:
   - Updated to test `fetch_events_by_tag_id` instead of `search_markets`
   - Updated data structures to match market format (slug, question, description, clobTokenIds)
   - Removed logging-related mocks

3. **test_process_and_rank_markets.py**:
   - Updated mocks to use `RankedMarkets` model
   - Removed `execution_trace` assertions
   - Removed logging-related mocks

4. **test_evaluate_markets.py**:
   - Updated mocks to use `ApprovedMarkets` model
   - Added assertions for `market_approved` and `market_research_complete` events
   - Removed `execution_trace` assertions
   - Removed logging-related mocks

5. **test_market_research_subgraph_integration.py**:
   - Updated to use tag-based flow
   - Mocks `fetch_tags_batch` and `fetch_events_by_tag_id`
   - Updated mock responses to use proper models (`SelectedTags`, `RankedMarkets`, `ApprovedMarkets`)
   - Removed `_state_logger` patches

6. **test_market_research.py**:
   - Updated all tests to use tag-based flow
   - Updated fixtures to use proper models
   - Removed `_state_logger` patches
   - Updated streaming tests to check for new events

### Test Coverage

Tests now verify:
- Tag selection from batches
- Tag name to ID mapping
- Event fetching by tag ID
- Incremental market streaming
- Final reasoning event
- Fallback logic when LLM returns empty results
- Error handling

## Data Flow

### Before (Keyword-Based)
1. Generate Queries → Keywords (e.g., "zuckerberg", "meta")
2. Fetch Markets → `/public-search?q=keyword` → Events → Markets
3. Process & Rank → Rank markets by relevance
4. Evaluate → Approve markets

### After (Tag-Based)
1. Generate Market Queries → Fetch tag batches → LLM selects tags → Map to IDs → Stream `tag_selected`
2. Fetch Markets → `/events?tag_id={id}` → Events → Markets → Deduplicate
3. Process & Rank → Rank markets by relevance (with fallback)
4. Evaluate → Approve markets → Stream `market_approved` (incremental) → Stream `market_research_complete`

## Files Created/Modified

### Created
- `polyplexity/backend/features/TAG_BASED_MARKET_FETCHING.md` - This document

### Modified

**Core Implementation**:
- `polyplexity_agent/graphs/state.py` - Added `ai_response` field to `MarketResearchState`
- `polyplexity_agent/tools/polymarket.py` - Added tag fetching functions, normalization helper, comprehensive docstrings
- `polyplexity_agent/models.py` - Added `SelectedTags` model
- `polyplexity_agent/prompts/market_prompts.py` - Added `TAG_SELECTION_PROMPT`, updated ranking/evaluation prompts

**Nodes**:
- `polyplexity_agent/graphs/nodes/market_research/generate_market_queries.py` - Replaced keyword generation with tag selection, added streaming, docstrings
- `polyplexity_agent/graphs/nodes/market_research/fetch_markets.py` - Updated to use tag IDs, added docstrings
- `polyplexity_agent/graphs/nodes/market_research/process_and_rank_markets.py` - Added fallback logic, docstrings, removed logging
- `polyplexity_agent/graphs/nodes/market_research/evaluate_markets.py` - Added incremental streaming, fallback logic, docstrings, removed logging
- `polyplexity_agent/graphs/nodes/market_research/think_tangentially.py` → `generate_tangential_queries.py` - Renamed, moved inline import, added docstrings

**Subgraph**:
- `polyplexity_agent/graphs/subgraphs/market_research.py` - Removed tangential thinking loop, added docstrings, organized imports

**Documentation**:
- `polyplexity/backend/docs/STREAM_RULES.md` - Added `tag_selected`, `market_approved`, updated `market_research_complete`

**Tests**:
- `tests/graphs/nodes/market_research/test_generate_market_queries.py` - Updated for tag selection
- `tests/graphs/nodes/market_research/test_fetch_markets.py` - Updated for tag-based fetching
- `tests/graphs/nodes/market_research/test_process_and_rank_markets.py` - Updated for new models
- `tests/graphs/nodes/market_research/test_evaluate_markets.py` - Updated for incremental streaming
- `tests/integration/test_market_research_subgraph_integration.py` - Updated for tag-based flow
- `tests/subgraphs/test_market_research.py` - Updated for tag-based flow

## Key Benefits

1. **More Precise Discovery**: Tag-based approach leverages Polymarket's categorization system
2. **Better User Experience**: Incremental streaming provides real-time feedback
3. **Cleaner Code**: Comprehensive docstrings, organized imports, better structure
4. **Maintainability**: Clear separation of concerns, well-documented functions
5. **Backward Compatibility**: Tangential thinking still uses keyword-based approach
6. **Robust Fallbacks**: Multiple fallback mechanisms ensure markets are always returned

## Breaking Changes

### Removed Features
- Tangential thinking loop removed from active subgraph (node still exists but unused)
- Intermediate logging and trace events removed
- `execution_trace` field removed from node return values

### Changed Behavior
- `market_queries` now contains tag IDs (numeric strings) instead of keywords
- Market fetching uses tag IDs instead of keyword searches
- Streaming events are incremental instead of batched at the end

## Migration Notes

### For Frontend
- Listen for `tag_selected` event to show selected tags
- Listen for `market_approved` events (multiple) to show markets as they're approved
- Listen for `market_research_complete` event for final reasoning
- Remove handling for `chosen_market` events (replaced by `market_approved`)

### For Developers
- Tag IDs are strings (e.g., "625", "207")
- Tag names must match exactly as shown in batch (case-sensitive in structured output, normalized for matching)
- Fallback logic ensures markets are always returned even if LLM returns empty results

## Future Improvements

- Add caching for tag batches to reduce API calls
- Implement parallel tag fetching for faster selection
- Add tag popularity/trending metrics to guide selection
- Enhance tag selection prompt with examples
- Add retry logic for tag fetching failures
- Consider tag hierarchies for more sophisticated selection
