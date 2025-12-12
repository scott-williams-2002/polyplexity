# Market Research Subgraph Implementation Summary

## Overview

This document summarizes the implementation of the market research subgraph that finds relevant prediction markets from Polymarket based on user queries and AI-generated reports.

## Key Changes

### 1. Fixed Structured Output

**Problem**: The `generate_market_queries.py` node was using `Dict[str, List[str]]` for structured output, which doesn't work reliably with LangChain's structured output system.

**Solution**: 
- Created `MarketQueries` Pydantic model in `models.py`
- Updated `generate_market_queries.py` to use `MarketQueries` with `.with_retry()` for reliability
- Updated prompt to mention structured output tool

**Files Modified**:
- `polyplexity_agent/models.py` - Added `MarketQueries`, `RankedMarkets`, `ApprovedMarkets` models
- `polyplexity_agent/graphs/nodes/market_research/generate_market_queries.py` - Fixed structured output
- `polyplexity_agent/prompts/market_prompts.py` - Updated prompt

### 2. Slug-Based Selection Approach

**Problem**: Having the LLM return full market objects risked losing important fields (clobTokenIds, images, descriptions, etc.).

**Solution**: 
- LLM now returns only market slugs + reasoning
- We deterministically piece together full market data from API responses using slugs
- This ensures no data loss and preserves all fields

**Implementation**:
- Created `RankedMarkets` and `ApprovedMarkets` Pydantic models that return slugs + reasoning
- Updated `process_and_rank_markets_node` to extract slugs, pass to LLM, then lookup full data
- Updated `evaluate_markets_node` to use the same slug-based approach
- Updated prompts to instruct LLM to return only slugs

**Files Modified**:
- `polyplexity_agent/models.py` - Added slug-based models
- `polyplexity_agent/graphs/nodes/market_research/process_and_rank_markets.py` - Slug-based ranking
- `polyplexity_agent/graphs/nodes/market_research/evaluate_markets.py` - Slug-based evaluation
- `polyplexity_agent/prompts/market_prompts.py` - Updated prompts for slug selection

### 3. Enhanced Market Data Extraction

**Problem**: Market data from Polymarket API needed better extraction to include all relevant fields for frontend display.

**Solution**:
- Enhanced `_extract_market_data()` to parse `clobTokenIds` from JSON string to list
- Extract `image` and `icon` fields (with fallback to event image)
- Preserve all market fields: `description`, `conditionId`, `liquidity`, `volume`, `outcomes`, `outcomePrices`
- Include event context (eventTitle, eventSlug, eventImage) in each market

**Files Modified**:
- `polyplexity_agent/tools/polymarket.py` - Enhanced data extraction
- `polyplexity_agent/graphs/nodes/market_research/fetch_markets.py` - Flatten markets from events

### 4. Market Structure Flattening

**Problem**: Markets were nested inside events, making it difficult to process individual markets.

**Solution**:
- Updated `fetch_markets_node` to flatten markets from events into a single list
- Each market includes event context (eventTitle, eventSlug, eventImage)
- Deduplication by market slug
- Store flat list of market dictionaries in `raw_events`

**Files Modified**:
- `polyplexity_agent/graphs/nodes/market_research/fetch_markets.py` - Flatten structure

### 5. Improved Query Generation Prompt

**Problem**: Initial prompts generated long, complex queries that caused API errors (403 Forbidden).

**Solution**: 
- Updated prompt to generate simple 1-2 word keyword phrases
- Emphasized tangential thinking - not just literal keyword matching
- Encourages thinking about related people, companies, and broader categories
- Example: For "React" → think about Meta/Facebook/Zuckerberg (React's creator)

**Key Features**:
- Simple 1-2 word queries (e.g., "zuckerberg", "meta", "tech")
- Tangential associations (React → Meta/Facebook)
- Broader categories when specific matches don't exist
- Examples of good vs bad queries

**Files Modified**:
- `polyplexity_agent/prompts/market_prompts.py` - Updated `MARKET_QUERY_GENERATION_PROMPT`

### 6. Testing Script

**Created**: `run_graphs/run_market_research.py`

A standalone script to test the market research subgraph with real LLM calls:
- Hardcodes user request and AI-generated report
- Runs the full subgraph workflow
- Streams events to console
- Displays results summary with approved markets
- Saves detailed state logs

**Usage**:
```bash
cd polyplexity/backend
python run_graphs/run_market_research.py
```

## Data Flow

1. **Generate Queries**: User topic → `MarketQueries` (list of simple keyword strings)
2. **Fetch Markets**: Queries → Polymarket API → Flat list of full market objects with all fields
3. **Rank Markets**: Market slugs + questions → `RankedMarkets` (slugs + reasoning) → Lookup full data → `candidate_markets`
4. **Evaluate Markets**: Candidate slugs + questions → `ApprovedMarkets` (slugs + reasoning) → Lookup full data → `approved_markets`

## Key Benefits

- **No data loss**: LLM only handles slugs, we deterministically assemble data
- **Simpler models**: Just slugs + reasoning, not complex nested objects
- **Complete data**: All API fields preserved (clobTokenIds, images, descriptions, etc.)
- **Reasoning preserved**: LLM reasoning stored in `reasoning_trace` for transparency
- **Better search**: Simple keywords with tangential thinking find more relevant markets
- **Frontend ready**: Approved markets include all fields needed for UI display

## Market Data Structure

Each approved market includes:
- `question`: Market question text
- `slug`: Market identifier
- `clobTokenIds`: List of token IDs (parsed from JSON)
- `description`: Market rules and description
- `image`: Market image URL
- `conditionId`: Market condition ID
- `liquidity`: Market liquidity
- `volume`: Trading volume
- `outcomes`: List of possible outcomes (parsed from JSON)
- `outcomePrices`: List of outcome prices (parsed from JSON)
- `eventTitle`: Parent event title
- `eventSlug`: Parent event slug
- `eventImage`: Parent event image

## Files Created/Modified

### Created
- `polyplexity/backend/run_graphs/run_market_research.py` - Testing script

### Modified
- `polyplexity_agent/models.py` - Added Pydantic models
- `polyplexity_agent/graphs/nodes/market_research/generate_market_queries.py` - Fixed structured output
- `polyplexity_agent/graphs/nodes/market_research/fetch_markets.py` - Flatten markets
- `polyplexity_agent/graphs/nodes/market_research/process_and_rank_markets.py` - Slug-based ranking
- `polyplexity_agent/graphs/nodes/market_research/evaluate_markets.py` - Slug-based evaluation
- `polyplexity_agent/tools/polymarket.py` - Enhanced data extraction
- `polyplexity_agent/prompts/market_prompts.py` - Updated all prompts

## Testing

The subgraph can be tested using:
```bash
cd polyplexity/backend
python run_graphs/run_market_research.py
```

The script uses hardcoded user request and AI report, runs the full workflow, and displays results.

## Future Improvements

- Add retry logic for API failures
- Implement rate limiting for Polymarket API
- Add caching for repeated queries
- Parallelize market fetching for multiple queries
- Add more sophisticated deduplication
- Enhance error handling and validation
