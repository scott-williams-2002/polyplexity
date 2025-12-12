# Market Research Main Graph Integration

## Overview

This document describes the integration of the market research subgraph into the main agent graph as a final step after generating the final report. The integration enables the agent to automatically discover and recommend relevant Polymarket prediction markets based on the user's question and the AI's response.

## Goal

Integrate the market research subgraph as the final step in the main agent workflow, allowing it to:
1. Receive the user's original question and the AI's final report
2. Discover relevant Polymarket markets through tag-based search
3. Generate a convincing, salesman-like recommendation connecting the user's question to approved markets
4. Stream all events to the frontend for real-time UI updates

## Architecture

### Graph Flow

The main agent graph flow was extended:

```
... → final_report → call_market_research → rewrite_polymarket_response → summarize_conversation → END
```

### State Management

**SupervisorState** (main graph state) was extended with:
- `polymarket_blurb: Optional[str]` - The final convincing recommendation text
- `approved_markets: List[Dict]` - List of approved markets from market research subgraph

**MarketResearchState** (subgraph state):
- `original_topic: str` - User's original question (mapped from `user_request`)
- `ai_response: str` - AI's final report (mapped from `final_report`)
- `approved_markets: List[Dict]` - Markets approved by evaluation node

### Data Handoff

**Main Graph → Subgraph:**
- `user_request` → `original_topic`
- `final_report` → `ai_response`

**Subgraph → Main Graph:**
- `approved_markets` → `approved_markets` (via return value)

## Implementation

### 1. New Nodes

#### `call_market_research_node`

**Location**: `polyplexity_agent/graphs/nodes/supervisor/call_market_research.py`

**Responsibilities**:
- Invoke market research subgraph with user question and final report
- Forward all subgraph events to main graph stream using `get_stream_writer()`
- Extract `approved_markets` from subgraph final state
- Emit `market_research_start` custom event
- Return `approved_markets` and `execution_trace` updates

**Key Implementation Details**:
- Uses `market_research_graph.stream()` with `stream_mode=["custom", "values"]`
- Iterates through stream chunks, forwarding custom events via `get_stream_writer()`
- Collects `approved_markets` from final `values` chunk
- Includes robust error handling with `stream_custom_event("error", ...)`

#### `rewrite_polymarket_response_node`

**Location**: `polyplexity_agent/graphs/nodes/supervisor/rewrite_polymarket_response.py`

**Responsibilities**:
- Generate a convincing, salesman-like blurb connecting user's question to approved markets
- Use LLM with `POLYMARKET_BLURB_PROMPT_TEMPLATE` to generate recommendation
- Emit `polymarket_blurb_generated` custom event
- Return `polymarket_blurb` and `execution_trace` updates

**Key Implementation Details**:
- Checks if `approved_markets` is empty; if so, emits `polymarket_blurb_skipped` and returns early
- Formats market information using `_format_markets_info()` helper
- Generates blurb using `_generate_polymarket_blurb()` helper with LLM
- Includes error handling

### 2. Prompt Template

**Location**: `polyplexity_agent/prompts/response_generator.py`

**Template**: `POLYMARKET_BLURB_PROMPT_TEMPLATE`

**Purpose**: Generate a convincing recommendation that connects the user's question to relevant Polymarket markets, written in a salesman-like style.

**Example Output Style**:
- "Based on your question about hot rods, you might be interested in testing your knowledge on this Polymarket market about NASCAR because..."
- "We just talked about the history of sports in my response, you should check out what people think the Mavericks game result will be..."

### 3. Graph Wiring

**Location**: `polyplexity_agent/graphs/agent_graph.py`

**Changes**:
- Added imports for `call_market_research_node` and `rewrite_polymarket_response_node`
- Added nodes to `StateGraph` builder
- Modified graph edges:
  - `final_report` → `call_market_research`
  - `call_market_research` → `rewrite_polymarket_response`
  - `rewrite_polymarket_response` → `summarize_conversation`

### 4. Entrypoint Updates

**Location**: `polyplexity_agent/entrypoint.py`

**Changes**:
- Imported `set_market_research_logger` from market research subgraph
- Called `set_market_research_logger(_state_logger)` to ensure subgraph uses global state logger
- Ensures consistent logging across main graph and subgraph

### 5. State Schema Updates

**Location**: `polyplexity_agent/graphs/state.py`

**Changes**:
- Added `polymarket_blurb: Optional[str]` to `SupervisorState`
- Added `approved_markets: List[Dict]` to `SupervisorState`

## Event Streaming

### Backend Streaming

All events from the market research subgraph are forwarded to the main graph stream:

1. **Subgraph Events**:
   - `tag_selected` - When tags are selected for market search
   - `market_approved` - When a market is approved (multiple events)
   - `market_research_complete` - When market research completes

2. **Main Graph Events**:
   - `market_research_start` - When market research begins
   - `polymarket_blurb_generated` - When the recommendation blurb is generated
   - `polymarket_blurb_skipped` - When no markets are found

3. **Event Forwarding**:
   - Subgraph events are captured via `market_research_graph.stream()` iterator
   - Events are forwarded using `get_stream_writer()` from LangGraph
   - Events flow through `entrypoint.py` → `sse.py` → frontend

### Frontend Display

**Location**: `polyplexity/frontend/hooks/useChatStream.ts` and `polyplexity/frontend/lib/adapters.ts`

**Implementation**:
- Added event handlers in `useChatStream.ts` to update `currentStatus` and `stage` for market research events
- Added handlers in `executionTraceToReasoning()` in `adapters.ts` to display market research events in the reasoning accordion

**Events Displayed**:
- `market_research_start` → "Starting market research..."
- `tag_selected` → "Selected X relevant market tags"
- `market_approved` → "Found market: [question]"
- `market_research_complete` → "Market research complete: [reasoning]"
- `polymarket_blurb_generated` → "Generated market recommendations"

## Debugging Process

### Issue: Market Research Events Not Visible in Frontend

**Symptom**: Market research events were being emitted and logged in backend state logs, but not appearing in the frontend UI.

### Debugging Approach

#### Phase 1: Backend Verification

**Hypotheses Tested**:
1. **(A)** Subgraph events not received in `call_market_research_node` - **REJECTED** (logs confirmed events received)
2. **(B)** Events in wrong format - **REJECTED** (logs confirmed correct envelope format)
3. **(C)** `get_stream_writer()` returns `None` - **REJECTED** (logs confirmed writer available)
4. **(D)** Events forwarded but filtered downstream - **INVESTIGATED**
5. **(E)** Subgraph events emitted but not captured by iterator - **REJECTED** (logs confirmed events captured)

**Instrumentation Added**:
- `call_market_research.py`: Logs for stream chunk reception, event processing, writer status, event forwarding
- `entrypoint.py`: Logs for main graph stream chunk reception, custom event processing, yielding to SSE generator
- `sse.py`: Logs for SSE generator chunk reception, SSE event formatting

**Result**: Backend logs confirmed that market research events were successfully flowing through the entire backend pipeline, including being formatted for SSE. The issue was determined to be frontend-side.

#### Phase 2: Frontend Investigation

**Root Cause Identified**: 
- Events were being received and normalized correctly
- Events were being added to `executionTrace` state
- However, `executionTraceToReasoning()` function in `adapters.ts` did not have handlers for market research events
- Therefore, events existed in state but were not displayed in the reasoning accordion

**Fix Applied**:
1. Added event handlers in `useChatStream.ts` to update UI status for market research events
2. Added handlers in `executionTraceToReasoning()` in `adapters.ts` to convert market research events to displayable text in the reasoning accordion

**Verification**: After fix, events were confirmed visible in the frontend reasoning accordion.

### Key Learnings

1. **Event Flow**: Subgraph events are correctly forwarded through the backend pipeline when using `get_stream_writer()`
2. **Frontend Display**: Events must be handled in both:
   - `useChatStream.ts` - For UI status updates
   - `executionTraceToReasoning()` - For display in reasoning accordion
3. **Type Safety**: Frontend TypeScript types must match backend event payload structure (fixed `SSEEvent` type issues)

## Code Standards Compliance

### Coding Style

- Followed `CODING_STYLE.md` guidelines:
  - Function length limits
  - Type hinting
  - Docstrings
  - Error handling patterns

### Streaming Rules

- Followed `STREAM_RULES.md` guidelines:
  - Standardized envelope format for events
  - Proper event naming conventions
  - Event payload structure
  - Error event emission

## Files Modified

### Backend

1. `polyplexity_agent/graphs/state.py` - Added state fields
2. `polyplexity_agent/graphs/nodes/supervisor/call_market_research.py` - New node
3. `polyplexity_agent/graphs/nodes/supervisor/rewrite_polymarket_response.py` - New node
4. `polyplexity_agent/graphs/nodes/supervisor/__init__.py` - Added exports
5. `polyplexity_agent/graphs/agent_graph.py` - Added nodes and edges
6. `polyplexity_agent/prompts/response_generator.py` - Added prompt template
7. `polyplexity_agent/entrypoint.py` - Added logger setup

### Frontend

1. `polyplexity/frontend/hooks/useChatStream.ts` - Added event handlers for UI status updates
2. `polyplexity/frontend/lib/adapters.ts` - Added handlers for reasoning display

## Testing

### Manual Testing

1. Send a query that triggers market research (e.g., "write a research report on what Obama has done")
2. Verify market research events appear in reasoning accordion
3. Verify `polymarket_blurb` is generated and included in final response
4. Verify events stream correctly to frontend

### State Logs

State logs in `polyplexity_agent/state_logs/` confirm:
- Market research subgraph executes correctly
- Events are emitted and forwarded
- `approved_markets` are collected
- `polymarket_blurb` is generated

## Future Improvements

1. **Error Handling**: Add retry logic for transient API failures
2. **Rate Limiting**: Implement rate limiting for Polymarket API calls
3. **Caching**: Cache tag selections and market evaluations
4. **Performance**: Parallelize market fetching where possible
5. **UI Enhancements**: Display market cards with links to Polymarket

## Related Documentation

- `TAG_BASED_MARKET_FETCHING.md` - Details on tag-based market discovery
- `MARKET_RESEARCH_IMPLEMENTATION.md` - Market research subgraph implementation
- `STREAM_RULES.md` - Event streaming standards
- `CODING_STYLE.md` - Coding standards
