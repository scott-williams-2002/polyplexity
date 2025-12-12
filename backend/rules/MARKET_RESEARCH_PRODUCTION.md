# Market Research Subgraph Production Readiness Guide

## Overview

This document outlines the steps required to make the market research subgraph production-ready and integrate it with the main agent graph.

## Current Status

The market research subgraph (`polyplexity_agent/graphs/subgraphs/market_research.py`) is implemented and testable, but not yet integrated into the main agent graph. It operates as a standalone subgraph that can be invoked independently.

## Production Readiness Checklist

### 1. Error Handling ✅ / ⚠️

**Status**: Partially Complete

**Current State**:
- Nodes have try/except blocks that emit error events
- Errors are logged via structlog logger
- Errors are re-raised (following coding style)

**Required Improvements**:
- [ ] Add retry logic for transient API failures (Polymarket API, LLM API)
- [ ] Add circuit breaker pattern for repeated failures
- [ ] Validate API responses before processing
- [ ] Handle rate limit errors gracefully (429 status codes)
- [ ] Add timeout handling for long-running LLM calls
- [ ] Validate state transitions (ensure required fields exist)

**Example Implementation**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def _fetch_markets_with_retry(query: str) -> List[Dict]:
    """Fetch markets with automatic retry on failure."""
    return search_markets(query)
```

### 2. Rate Limiting ⚠️

**Status**: Not Implemented

**Required**:
- [ ] Add rate limiting for Polymarket API calls
- [ ] Implement exponential backoff for rate limit errors
- [ ] Add rate limit tracking per API endpoint
- [ ] Configure rate limits via Settings

**Implementation Approach**:
- Use `ratelimit` library or custom decorator
- Track API call timestamps
- Respect API rate limits (check Polymarket API docs)
- Add configuration in `Settings` class

**Example**:
```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=10, period=60)  # 10 calls per minute
def search_markets(query: str) -> List[Dict]:
    """Search markets with rate limiting."""
    # ... implementation
```

### 3. Input/Output Validation ⚠️

**Status**: Partially Complete

**Current State**:
- State schema defined via TypedDict
- LLM outputs use structured output (Pydantic models)

**Required Improvements**:
- [ ] Validate `original_topic` is non-empty string
- [ ] Validate `market_queries` is non-empty list before fetching
- [ ] Validate `raw_events` structure matches expected format
- [ ] Validate `candidate_markets` before ranking
- [ ] Add Pydantic models for market data structures
- [ ] Validate LLM structured outputs match expected schema

**Example**:
```python
from pydantic import BaseModel, Field, validator

class MarketEvent(BaseModel):
    """Validated market event structure."""
    title: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1)
    description: str
    markets: List[Dict] = Field(default_factory=list)
    
    @validator("slug")
    def validate_slug(cls, v):
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Slug must be alphanumeric with dashes/underscores")
        return v
```

### 4. Monitoring & Observability ⚠️

**Status**: Basic Logging Exists

**Current State**:
- StateLogger writes detailed state dumps (local debugging)
- structlog logger for application events
- Trace events emitted for execution tracking

**Required Improvements**:
- [ ] Add metrics for subgraph execution time
- [ ] Track API call latencies (Polymarket, LLM)
- [ ] Monitor market query generation success rate
- [ ] Track market approval/rejection rates
- [ ] Add distributed tracing (OpenTelemetry)
- [ ] Add performance metrics (markets found per query, etc.)
- [ ] Alert on error rate thresholds

**Implementation**:
- Use `prometheus_client` for metrics
- Add timing decorators for node execution
- Track metrics in structured logger

### 5. Configuration ⚠️

**Status**: Basic Configuration Exists

**Current State**:
- LLM model configured via Settings
- API keys via environment variables

**Required Improvements**:
- [ ] Make LLM model configurable per node (if needed)
- [ ] Add configuration for max markets to fetch
- [ ] Add configuration for market evaluation criteria
- [ ] Add configuration for query generation parameters
- [ ] Document all configuration options
- [ ] Add validation for configuration values

**Example Settings Addition**:
```python
class Settings(BaseSettings):
    # ... existing settings
    market_research_max_queries: int = 5
    market_research_max_markets: int = 20
    market_research_evaluation_strictness: str = "medium"  # low, medium, high
```

### 6. Testing ✅ / ⚠️

**Status**: Unit Tests Exist, E2E Test Created

**Current State**:
- Unit tests for each node (`tests/graphs/nodes/market_research/`)
- Integration test with mocked APIs (`tests/integration/test_market_research_subgraph_integration.py`)
- E2E test with real APIs (`tests/market_research_e2e/test_run_market_research.py`)

**Required Improvements**:
- [ ] Add tests for error scenarios (API failures, invalid inputs)
- [ ] Add tests for rate limiting behavior
- [ ] Add performance tests (latency benchmarks)
- [ ] Add tests for edge cases (empty results, malformed data)
- [ ] Add load tests (concurrent executions)
- [ ] Add tests for state validation

### 7. Performance Optimization ⚠️

**Status**: Sequential Execution

**Current State**:
- Queries are generated sequentially
- Markets are fetched sequentially per query
- Processing is sequential

**Required Improvements**:
- [ ] Parallelize market fetching for multiple queries
- [ ] Add caching for repeated queries (Redis/Memory)
- [ ] Optimize LLM calls (batch if possible)
- [ ] Add early termination if enough markets found
- [ ] Optimize market deduplication algorithm

**Example Parallel Fetching**:
```python
from concurrent.futures import ThreadPoolExecutor

def fetch_markets_node(state: MarketResearchState):
    """Fetch markets in parallel for all queries."""
    queries = state["market_queries"]
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(search_markets, queries)
    
    all_events = []
    for result in results:
        all_events.extend(result)
    
    # ... deduplication logic
```

### 8. Streaming Integration ✅

**Status**: Complete

**Current State**:
- Nodes emit trace events via `stream_trace_event()`
- Nodes emit custom events via `stream_custom_event()`
- Events are in standardized envelope format
- Subgraph events can be forwarded to main graph

**No Changes Required**: Streaming is production-ready.

### 9. State Management ⚠️

**Status**: Basic State Management

**Current State**:
- State schema defined via TypedDict
- State logger for debugging
- No checkpointing for subgraph (standalone)

**Required for Main Graph Integration**:
- [ ] Ensure state logger is set from main graph (already done)
- [ ] Handle state mapping from SupervisorState to MarketResearchState
- [ ] Map results back to SupervisorState
- [ ] Ensure execution_trace is collected properly

### 10. Main Graph Integration ⚠️

**Status**: Not Integrated

**Current State**:
- Market research subgraph exists independently
- No node in main graph calls it
- No routing logic to invoke it

**Required Steps**:

#### Step 1: Create `call_market_research_node`

Create `polyplexity_agent/graphs/nodes/supervisor/call_market_research.py`:

```python
"""
Call market research node for the main agent graph.

Invokes the market research subgraph with the current research topic.
"""
from polyplexity_agent.streaming.event_serializers import create_trace_event
from polyplexity_agent.graphs.state import SupervisorState
from polyplexity_agent.graphs.subgraphs.market_research import (
    market_research_graph,
    set_state_logger as set_market_research_logger,
)
from polyplexity_agent.logging import get_logger
from polyplexity_agent.streaming import stream_custom_event, stream_trace_event
from polyplexity_agent.utils.helpers import log_node_state
from polyplexity_agent.utils.state_manager import _state_logger

logger = get_logger(__name__)


def call_market_research_node(state: SupervisorState):
    """Invokes the market research subgraph with the current research topic."""
    try:
        log_node_state(
            _state_logger,
            "call_market_research",
            "MAIN_GRAPH",
            dict(state),
            "BEFORE",
            state.get("iterations", 0),
            f"Topic: {state.get('next_topic', 'N/A')}"
        )
        
        topic = state["next_topic"]
        set_market_research_logger(_state_logger)
        
        node_call_event = create_trace_event(
            "node_call",
            "call_market_research",
            {"topic": topic}
        )
        stream_trace_event("node_call", "call_market_research", {"topic": topic})
        
        approved_markets = []
        
        for mode, data in market_research_graph.stream(
            {"original_topic": topic},
            stream_mode=["custom", "values"]
        ):
            if mode == "custom":
                items = data if isinstance(data, list) else [data]
                for item in items:
                    from langgraph.config import get_stream_writer
                    writer = get_stream_writer()
                    if writer:
                        writer(item)
            elif mode == "values":
                if "approved_markets" in data:
                    approved_markets = data["approved_markets"]
        
        result = {
            "prediction_markets": approved_markets,
            "execution_trace": [node_call_event]
        }
        
        log_node_state(
            _state_logger,
            "call_market_research",
            "MAIN_GRAPH",
            {**state, **result},
            "AFTER",
            state.get("iterations", 0),
            f"Found {len(approved_markets)} approved markets"
        )
        
        return result
    except Exception as e:
        stream_custom_event(
            "error",
            "call_market_research",
            {"error": str(e), "topic": state.get("next_topic", "N/A")}
        )
        logger.error(
            "call_market_research_node_error",
            error=str(e),
            topic=state.get("next_topic", "N/A"),
            exc_info=True
        )
        raise
```

#### Step 2: Add Node to Main Graph

Update `polyplexity_agent/graphs/agent_graph.py`:

```python
from polyplexity_agent.graphs.nodes.supervisor.call_market_research import (
    call_market_research_node,
)

# In create_agent_graph():
builder.add_node("call_market_research", call_market_research_node)
```

#### Step 3: Add Routing Logic

Update supervisor node to decide when to call market research:

- Add decision field to `SupervisorDecision` model (optional)
- Or add conditional routing in supervisor based on user request
- Example: If user asks about prediction markets, route to market research

#### Step 4: Update SupervisorState

Ensure `SupervisorState` includes `prediction_markets` field (already exists).

### 11. Documentation ⚠️

**Status**: Basic Documentation Exists

**Required Improvements**:
- [ ] Add usage examples in `polyplexity_agent/docs/USAGE.md`
- [ ] Document API integration (Polymarket API)
- [ ] Document configuration options
- [ ] Add troubleshooting guide
- [ ] Document error codes and meanings
- [ ] Add architecture diagram showing integration

## Implementation Priority

### Phase 1: Core Functionality (High Priority)
1. Main graph integration (Step 10)
2. Error handling improvements (Step 1)
3. Input/output validation (Step 3)

### Phase 2: Production Hardening (Medium Priority)
4. Rate limiting (Step 2)
5. Performance optimization (Step 7)
6. Monitoring (Step 4)

### Phase 3: Polish (Lower Priority)
7. Configuration expansion (Step 5)
8. Additional tests (Step 6)
9. Documentation (Step 11)

## Testing Strategy

### Unit Tests
- Test each node independently with mocked dependencies
- Test error handling paths
- Test validation logic

### Integration Tests
- Test subgraph end-to-end with mocked APIs
- Test main graph integration
- Test state transitions

### E2E Tests
- Test with real APIs (use test environment)
- Test streaming output
- Test error recovery

### Performance Tests
- Benchmark subgraph execution time
- Test with various topic lengths
- Test with various result sizes

## Deployment Checklist

Before deploying to production:

- [ ] All Phase 1 items completed
- [ ] Rate limiting configured and tested
- [ ] Monitoring dashboards created
- [ ] Error alerting configured
- [ ] Performance benchmarks established
- [ ] Documentation updated
- [ ] Integration tests passing
- [ ] Load tests completed
- [ ] Rollback plan documented

## Notes

- The subgraph is currently standalone and can be tested independently
- Integration with main graph requires creating `call_market_research_node`
- Follow the pattern used by `call_researcher_node` for consistency
- Ensure streaming events are properly forwarded to main graph
- State logger should be shared from main graph (already implemented)
