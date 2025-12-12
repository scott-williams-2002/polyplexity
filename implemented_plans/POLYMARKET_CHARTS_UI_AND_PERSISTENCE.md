# Polymarket Charts UI and Persistence Implementation

## Overview

This document describes the implementation of dynamic Polymarket chart rendering in the frontend UI, along with persistence fixes to ensure market data and charts persist when loading thread history. The implementation enables real-time display of market price history charts with interactive features and ensures all market data is properly stored and restored.

## Goal

1. Dynamically render Polymarket price history charts when SSE events contain `approved_markets`
2. Display market data and charts beneath AI responses
3. Persist `approved_markets` and `polymarket_blurb` in execution trace for restoration on page refresh
4. Extract and restore market data when loading thread history from database
5. Ensure all market-related data (charts, blurb, links) persists correctly

## Architecture

### Frontend Components

**Component Hierarchy:**
```
MessageBubble
  └─ MarketChartsContainer
      └─ PolymarketChart (one per market)
          ├─ Chart Area (left 70%)
          └─ Market Data Sidebar (right 30%)
```

**Data Flow:**
1. SSE events → `useChatStream` hook → extracts `approved_markets` and `polymarket_blurb`
2. Data flows to `App.tsx` → added to `Message` objects
3. `MessageBubble` renders `MarketChartsContainer` with market data
4. Each `PolymarketChart` fetches price history for all `clobTokenIds` in parallel
5. Charts display multiple lines (one per outcome/clobTokenId) with interactive highlighting

### Backend Persistence

**Execution Trace Collection:**
- `state_update` events with `approved_markets` and `polymarket_blurb` are collected in `entrypoint.py`
- Converted to trace events and added to `question_execution_trace`
- Persisted to database via `save_messages_and_trace()`
- Restored when loading thread history via `get_thread_history()`

## Implementation Details

### 1. Frontend Types and Services

**File**: `polyplexity/frontend/types.ts`

Added types:
- `ApprovedMarket` interface - Complete market data structure from SSE events
- `PricePoint` interface - Price history data point (timestamp, price)
- `PriceHistoryResponse` interface - API response format
- `polymarketBlurb?: string` field added to `Message` interface

**File**: `polyplexity/frontend/services/polymarketService.ts`

Created service function:
- `fetchPriceHistory(clobTokenId, interval='all', fidelity=720)` - Fetches price history from Polymarket API
- Uses `interval=all` and `fidelity=720` (minutes) for complete data coverage
- Properly encodes query parameters using URL constructor

### 2. Enhanced PolymarketChart Component

**File**: `polyplexity/frontend/components/PolymarketGraph.tsx`

**Key Features:**
- Accepts `market: ApprovedMarket` prop instead of single `clobTokenId`
- Fetches price history for all `clobTokenIds` in parallel using `Promise.all()`
- Renders multiple `Area` components (one per clobTokenId) with distinct colors
- Right sidebar displays raw JSON of complete market data
- Interactive features:
  - Hovering a line highlights corresponding sidebar entry
  - Clicking sidebar entry brightens corresponding line(s)
  - Visual feedback with brighter strokes and opacity for active lines
- Maps each clobTokenId to its outcome label using `outcomes` array index

**Color Palette:**
- 6 distinct colors for different outcomes
- Colors cycle if more than 6 outcomes exist

**Data Combination:**
- Combines all price points by timestamp for unified chart display
- Handles missing data points gracefully

### 3. MarketChartsContainer Component

**File**: `polyplexity/frontend/components/MarketChartsContainer.tsx`

- Accepts `markets: ApprovedMarket[]` prop
- Maps over markets and renders `PolymarketChart` for each
- Adds spacing between charts
- Handles empty state

### 4. SSE Event Parsing

**File**: `polyplexity/frontend/hooks/useChatStream.ts`

**Updates:**
- Added `approvedMarkets` state - populated from `state_update` events where `node === "call_market_research"`
- Added `polymarketBlurb` state - populated from `state_update` events where `node === "rewrite_polymarket_response"`
- Both states are returned from hook and reset on stream start/reset
- Events are normalized and added to `executionTrace` for persistence

### 5. Execution Trace Extraction

**File**: `polyplexity/frontend/lib/adapters.ts`

**New Functions:**
- `extractApprovedMarketsFromTrace(events)` - Finds `state_update` events with `node === "call_market_research"` and extracts `approved_markets`
- `extractPolymarketBlurbFromTrace(events)` - Finds `state_update` events with `node === "rewrite_polymarket_response"` and extracts `polymarket_blurb`
- `extractSearchLinksFromTrace(events)` - Extracts search result links from `search` type events

**Updated Functions:**
- `executionTraceToReasoning()` - Filters out `state_update` events containing `approved_markets` and `polymarket_blurb` (excluded from reasoning display but remain in trace)
- `apiMessageToViteMessage()` - Calls extraction functions and populates `approvedMarkets` and `polymarketBlurb` fields in returned `Message`

### 6. Message Integration

**File**: `polyplexity/frontend/App.tsx`

**Updates:**
- Gets `approvedMarkets` and `polymarketBlurb` from `useChatStream` hook
- Passes both to messages during streaming and finalization
- Preserves existing data when updating messages

**File**: `polyplexity/frontend/components/MessageBubble.tsx`

**Updates:**
- Displays `polymarketBlurb` as markdown-formatted text above charts
- Renders `MarketChartsContainer` beneath AI response content
- Both only render when data exists

### 7. Backend Persistence Fix

**File**: `polyplexity/backend/polyplexity_agent/entrypoint.py`

**Problem Identified:**
- `state_update` events with `approved_markets` and `polymarket_blurb` were streamed to frontend but NOT collected into `question_execution_trace`
- When `save_messages_and_trace()` was called, these events were missing
- Loading thread history resulted in empty execution trace for market data

**Solution:**
- Added detection for `call_market_research` node updates containing `approved_markets`
- Added detection for `rewrite_polymarket_response` node updates containing `polymarket_blurb`
- Created `state_update` trace events using `create_trace_event()` for both
- Added these trace events to `question_execution_trace` before saving
- Ensures market data is persisted and can be restored on page refresh

**Code Added:**
```python
# Collect state_update events for approved_markets and polymarket_blurb
if node_name == "call_market_research" and "approved_markets" in node_data:
    approved_markets = node_data.get("approved_markets")
    if isinstance(approved_markets, list) and len(approved_markets) > 0:
        state_update_event = create_trace_event(
            "state_update",
            "call_market_research",
            {"approved_markets": approved_markets}
        )
        question_execution_trace.append(state_update_event)

if node_name == "rewrite_polymarket_response" and "polymarket_blurb" in node_data:
    polymarket_blurb = node_data.get("polymarket_blurb")
    if isinstance(polymarket_blurb, str) and len(polymarket_blurb) > 0:
        state_update_event = create_trace_event(
            "state_update",
            "rewrite_polymarket_response",
            {"polymarket_blurb": polymarket_blurb}
        )
        question_execution_trace.append(state_update_event)
```

## Debugging Process

### Issue: Charts and Blurb Disappearing After Refresh

**Symptoms:**
- Charts and blurb rendered correctly during streaming
- After ~1 second (state refresh), charts and blurb disappeared
- Links persisted correctly

**Debugging Steps:**
1. Added instrumentation logs to track data flow:
   - `extractApprovedMarketsFromTrace()` - Logged event structure and extraction results
   - `extractPolymarketBlurbFromTrace()` - Logged event structure and extraction results
   - `apiMessageToViteMessage()` - Logged extraction results
   - `App.tsx` finalization - Logged data preservation
   - `useChatStream.reset()` - Logged data clearing

2. **Log Analysis Findings:**
   - During streaming: Data present (`approvedMarketsCount: 5`, `hasPolymarketBlurb: true`)
   - After finalization: Data preserved correctly
   - When loading history: Execution trace had 24 events but NO `state_update` events
   - Extraction functions found 0 approved markets and no blurb

3. **Root Cause Identified:**
   - Execution trace from database contained only `node_call`, `reasoning`, `custom`, and `search` events
   - Missing `state_update` events for `approved_markets` and `polymarket_blurb`
   - Backend was not collecting these state updates into execution trace

4. **Fix Applied:**
   - Updated `entrypoint.py` to detect and collect `state_update` events
   - Convert state updates to trace events and add to `question_execution_trace`
   - Ensures persistence to database

### Verification

**Post-Fix Verification:**
- Charts and blurb now persist after page refresh
- Execution trace includes `state_update` events when loading history
- Extraction functions successfully find market data
- All data (markets, blurb, links) persists correctly

## Files Modified

### Frontend
- `polyplexity/frontend/types.ts` - Added market types and `polymarketBlurb` field
- `polyplexity/frontend/services/polymarketService.ts` - Created with `fetchPriceHistory` function
- `polyplexity/frontend/components/PolymarketGraph.tsx` - Enhanced for multi-line charts with market data
- `polyplexity/frontend/components/MarketChartsContainer.tsx` - New component for multiple charts
- `polyplexity/frontend/components/MessageBubble.tsx` - Integrated charts and blurb display
- `polyplexity/frontend/hooks/useChatStream.ts` - Added market data state and parsing
- `polyplexity/frontend/lib/adapters.ts` - Added extraction functions and updated reasoning filter
- `polyplexity/frontend/App.tsx` - Passes market data to messages

### Backend
- `polyplexity/backend/polyplexity_agent/entrypoint.py` - Collects `state_update` events for persistence

## API Integration

### Polymarket Price History API

**Endpoint**: `https://clob.polymarket.com/prices-history`

**Query Parameters:**
- `market` (required) - The clobTokenId
- `interval` (default: `all`) - Time range for data (`all`, `max`, `1d`, `7d`, `30d`, etc.)
- `fidelity` (default: `720`) - Data resolution in minutes (720 = 12 hour intervals)

**Response Format:**
```json
{
  "history": [
    {
      "t": 1234567890,  // Unix timestamp
      "p": 0.65        // Price (0-1 range)
    }
  ]
}
```

## Testing Considerations

### Verified Functionality
- Charts render when `approved_markets` SSE events received
- Multiple markets display as separate chart components
- Each market shows all outcomes as separate lines
- Interactive hover/click highlighting works
- Raw JSON market data displays in sidebar
- Polymarket blurb displays above charts
- All data persists when loading thread history
- Links from search events persist correctly

### Edge Cases Handled
- Empty `approved_markets` array - No charts rendered
- Missing `polymarket_blurb` - Only charts shown
- Failed price history fetch for individual clobTokenId - Error handled gracefully, other tokens still render
- Multiple markets with same outcome names - Handled via clobTokenId mapping
- Missing execution trace - Graceful fallback, no errors

## Future Enhancements

Potential improvements:
1. Add loading states for individual chart data fetches
2. Add error retry logic for failed API calls
3. Cache price history data to reduce API calls
4. Add time range selector (1d, 7d, 30d, all)
5. Add chart zoom/pan functionality
6. Display volume/liquidity trends
7. Add market links to Polymarket website

## Summary

Successfully implemented dynamic Polymarket chart rendering with full persistence support. Charts display real-time price history for all market outcomes, with interactive features and complete market data visibility. All data (markets, blurb, links) now persists correctly when loading thread history, ensuring a seamless user experience across page refreshes.
