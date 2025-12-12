# Streaming Rules and Guidelines

This document defines the standardized streaming architecture for the polyplexity agent system. All streaming events follow a common envelope format and are emitted through centralized functions to ensure consistency and eliminate duplication.

## Table of Contents

1. [How: Functions and Format](#how-functions-and-format)
2. [Where: Who Calls It](#where-who-calls-it)
3. [When: At What Stage in Workflow](#when-at-what-stage-in-workflow)
4. [Event Type Reference](#event-type-reference)
5. [Examples](#examples)

---

## How: Functions and Format

### Standardized Envelope Format

All streaming events use a common envelope format:

```python
{
    "type": str,           # Event type (trace, custom, state_update, system, error, complete)
    "timestamp": int,      # Unix timestamp in milliseconds
    "node": str,           # Node name that generated the event
    "event": str,          # Specific event name (e.g., "supervisor_decision", "node_call")
    "payload": dict        # Event-specific data dictionary
}
```

### Streaming Functions

All nodes should use these functions from `polyplexity_agent.streaming`:

#### 1. `stream_trace_event(trace_type: str, node: str, data: dict)`

Stream a trace event (node calls, reasoning, searches, state updates).

**Parameters:**
- `trace_type`: One of `"node_call"`, `"reasoning"`, `"search"`, `"state_update"`, `"custom"`
- `node`: Name of the node emitting the event
- `data`: Event-specific data dictionary

**Example:**
```python
from polyplexity_agent.streaming import stream_trace_event

stream_trace_event("node_call", "supervisor", {})
stream_trace_event("reasoning", "supervisor", {"reasoning": "Need more research"})
stream_trace_event("search", "perform_search", {"query": "AI trends", "results": [...]})
```

#### 2. `stream_custom_event(event_name: str, node: str, data: dict)`

Stream a custom event (supervisor decisions, generated queries, etc.).

**Parameters:**
- `event_name`: Name of the custom event (e.g., `"supervisor_decision"`, `"generated_queries"`)
- `node`: Name of the node emitting the event
- `data`: Event-specific data dictionary

**Example:**
```python
from polyplexity_agent.streaming import stream_custom_event

stream_custom_event("supervisor_decision", "supervisor", {
    "decision": "research",
    "reasoning": "Need more information",
    "topic": "AI trends"
})

stream_custom_event("generated_queries", "generate_queries", {
    "queries": ["AI trends 2024", "machine learning advances"]
})
```

#### 3. `stream_state_update(node: str, update_data: dict)`

Stream a state update event (research notes added, iterations incremented, etc.).

**Parameters:**
- `node`: Name of the node that updated the state
- `update_data`: State update data dictionary

**Example:**
```python
from polyplexity_agent.streaming import stream_state_update

stream_state_update("call_researcher", {
    "research_notes": ["## Research on: AI trends\nSummary..."]
})
```

#### 4. `stream_event(event_type: str, node: str, event: str, payload: dict)`

Generic streaming function for any event type. Prefer the specific functions above when possible.

**Parameters:**
- `event_type`: Type of event (`"trace"`, `"custom"`, `"state_update"`, etc.)
- `node`: Name of the node emitting the event
- `event`: Specific event name
- `payload`: Event-specific data dictionary

### Event Type Values

- **`"trace"`**: Execution trace events (node calls, reasoning, searches)
- **`"custom"`**: Custom application events (decisions, queries, etc.)
- **`"state_update"`**: State changes (research notes, iterations, etc.)
- **`"system"`**: System events (thread_id, thread_name)
- **`"error"`**: Error events
- **`"complete"`**: Completion events

---

## Where: Who Calls It

### Single Source of Truth

**Events are emitted ONCE from nodes** - there is no duplication or auto-wrapping.

### Call Hierarchy

1. **Nodes** → Call streaming functions directly
   - All nodes (`supervisor`, `call_researcher`, `generate_queries`, etc.) call streaming functions
   - Events are automatically serialized into envelope format
   - No need to manually format events

2. **Entrypoint** → Processes events from LangGraph stream
   - `entrypoint.py` receives events from LangGraph stream
   - Uses `process_custom_events()` and `process_update_events()` to normalize events
   - Yields events to `main.py` for SSE formatting
   - Collects execution traces for DB persistence

3. **Main** → Formats events as SSE
   - `main.py` uses `create_sse_generator()` from streaming module
   - Converts envelope events to SSE format (`data: {json}\n\n`)
   - Handles completion and error events

### Important: No Duplication

- **DO NOT** manually wrap events in `entrypoint.py` - events are already in envelope format
- **DO NOT** create duplicate trace events - nodes emit them directly
- **DO NOT** use `get_stream_writer()` directly - use streaming functions instead

---

## When: At What Stage in Workflow

### After Any Novel Event

Stream events **immediately after** any novel event occurs:

1. **Node Execution** → Stream `node_call` trace event
2. **LLM Reasoning** → Stream `reasoning` trace event
3. **Custom Events** → Stream custom event (decisions, queries, etc.)
4. **State Changes** → Stream state update event
5. **Search Operations** → Stream `search` trace events
6. **Errors** → Stream error event

### Workflow Stages and Events

#### 1. Initialization Stage

**When:** At the start of agent execution

**Events:**
- `thread_id` (system event) - Emitted in `entrypoint.py` when thread is created
- `thread_name` (custom event) - Emitted in `supervisor_node` on first iteration

**Example:**
```python
# In entrypoint.py
if thread_id:
    yield ("custom", {"type": "system", "event": "thread_id", "payload": {"thread_id": thread_id}})

# In supervisor_node
if iteration == 0:
    stream_custom_event("thread_name", "supervisor", {"thread_id": thread_id, "name": thread_name})
```

#### 2. Supervisor Decision Stage

**When:** After supervisor node executes

**Events:**
- `node_call` (trace) - Node execution started
- `reasoning` (trace) - Supervisor reasoning
- `supervisor_decision` (custom) - Decision made

**Example:**
```python
# In supervisor_node
stream_trace_event("node_call", "supervisor", {})
stream_trace_event("reasoning", "supervisor", {"reasoning": decision.reasoning})
stream_custom_event("supervisor_decision", "supervisor", {
    "decision": decision.next_step,
    "reasoning": decision.reasoning,
    "topic": decision.research_topic
})
```

#### 3. Research Stage

**When:** During researcher subgraph execution

**Events:**
- `researcher_thinking` (custom) - Researcher starting to think
- `node_call` (trace) - Query generation started
- `generated_queries` (custom) - Queries generated
- `search_start` (custom) - Search query being executed
- `web_search_url` (custom) - Search result URL found
- `research_synthesis_done` (custom) - Research synthesis complete

**Example:**
```python
# In generate_queries_node
stream_custom_event("researcher_thinking", "generate_queries", {"topic": state['topic']})
stream_trace_event("node_call", "generate_queries", {})
stream_trace_event("custom", "generate_queries", {"event": "generated_queries", "queries": resp.queries})
stream_custom_event("generated_queries", "generate_queries", {"queries": resp.queries})

# In perform_search_node
stream_trace_event("node_call", "perform_search", {"query": query})
stream_trace_event("search", "perform_search", {"event": "search_start", "query": query})
stream_custom_event("search_start", "perform_search", {"query": query})
stream_custom_event("web_search_url", "perform_search", {"url": url, "markdown": markdown})
```

#### 4. Final Report Stage

**When:** During final report generation

**Events:**
- `node_call` (trace) - Report generation started
- `writing_report` (custom) - Report being written
- `final_report_complete` (custom) - Report complete

**Example:**
```python
# In final_report_node
stream_trace_event("node_call", "final_report", {})
stream_custom_event("writing_report", "final_report", {})
stream_trace_event("custom", "final_report", {"event": "final_report_complete", "report": final_report})
stream_custom_event("final_report_complete", "final_report", {"report": final_report})
```

#### 5. State Update Stage

**When:** After state changes occur

**Events:**
- `state_update` (trace) - State changed
- State update events (via LangGraph `updates` mode)

**Example:**
```python
# State updates are automatically converted to envelope format in entrypoint.py
# Nodes don't need to explicitly stream state updates - LangGraph handles this
```

#### 6. Error Stage

**When:** When an exception occurs

**Events:**
- `error` (custom) - Error occurred

**Example:**
```python
# In any node's exception handler
except Exception as e:
    stream_custom_event("error", "node_name", {"error": str(e)})
    raise
```

#### 7. Completion Stage

**When:** At the end of agent execution

**Events:**
- `complete` (system) - Execution complete

**Example:**
```python
# Automatically handled by create_sse_generator() in main.py
# No need to manually emit completion events
```

---

## Event Type Reference

### Trace Events

| Event Name | Type | Node | Payload | When |
|------------|------|------|---------|------|
| `node_call` | trace | Any | `{}` | When a node starts executing |
| `reasoning` | trace | supervisor | `{"reasoning": str}` | When supervisor makes a decision |
| `search` | trace | perform_search | `{"query": str, "results": [...]}` | When search is performed |
| `state_update` | trace | Any | `{"update": str, ...}` | When state changes |

### Custom Events

| Event Name | Type | Node | Payload | When |
|------------|------|------|---------|------|
| `thread_name` | custom | supervisor | `{"thread_id": str, "name": str}` | When thread name is generated |
| `supervisor_decision` | custom | supervisor | `{"decision": str, "reasoning": str, "topic": str}` | When supervisor decides next step |
| `researcher_thinking` | custom | generate_queries | `{"topic": str}` | When researcher starts thinking |
| `generated_queries` | custom | generate_queries | `{"queries": List[str]}` | When search queries are generated |
| `generated_market_queries` | custom | generate_market_queries | `{"queries": List[str]}` | When market queries are generated |
| `search_start` | custom | perform_search | `{"query": str}` | When a search query starts |
| `web_search_url` | custom | perform_search | `{"url": str, "markdown": str}` | When a search result URL is found |
| `research_synthesis_done` | custom | synthesize_research | `{"summary": str}` | When research synthesis completes |
| `writing_report` | custom | final_report | `{}` | When final report generation starts |
| `final_report_complete` | custom | final_report, direct_answer, clarification | `{"report": str}` | When final report is complete |
| `error` | custom | Any | `{"error": str}` | When an error occurs |

### State Update Events

| Event Name | Type | Node | Payload | When |
|------------|------|------|---------|------|
| `research_notes_added` | state_update | call_researcher | `{"research_notes": List[str]}` | When research notes are added |
| `iterations_incremented` | state_update | supervisor | `{"iterations": int}` | When iteration count increases |
| `final_report_update` | state_update | final_report | `{"final_report": str}` | When final report is updated |

### System Events

| Event Name | Type | Node | Payload | When |
|------------|------|------|---------|------|
| `thread_id` | system | system | `{"thread_id": str}` | When thread ID is created |
| `complete` | complete | system | `{"response": str}` | When execution completes |

---

## Examples

### Example 1: Supervisor Node

```python
from polyplexity_agent.streaming import stream_trace_event, stream_custom_event

def supervisor_node(state: SupervisorState):
    # Stream node call
    stream_trace_event("node_call", "supervisor", {})
    
    # Make decision
    decision = _make_supervisor_decision(state, iteration)
    
    # Stream reasoning
    stream_trace_event("reasoning", "supervisor", {"reasoning": decision.reasoning})
    
    # Stream decision
    stream_custom_event("supervisor_decision", "supervisor", {
        "decision": decision.next_step,
        "reasoning": decision.reasoning,
        "topic": decision.research_topic
    })
    
    return {"next_topic": decision.research_topic}
```

### Example 2: Search Node

```python
from polyplexity_agent.streaming import stream_trace_event, stream_custom_event

def perform_search_node(state: dict):
    query = state["query"]
    
    # Stream node call
    stream_trace_event("node_call", "perform_search", {"query": query})
    
    # Stream search start
    stream_trace_event("search", "perform_search", {"event": "search_start", "query": query})
    stream_custom_event("search_start", "perform_search", {"query": query})
    
    # Perform search
    results = _perform_search_tavily(query)
    
    # Stream search results
    stream_trace_event("search", "perform_search", {"results": [...]})
    
    # Stream URLs
    for res in results.get("results", []):
        if res.get("url"):
            stream_custom_event("web_search_url", "perform_search", {
                "url": res["url"],
                "markdown": format_search_url_markdown(res["url"])
            })
    
    return {"search_results": [...]}
```

### Example 3: Error Handling

```python
from polyplexity_agent.streaming import stream_custom_event

def some_node(state):
    try:
        # ... node logic ...
        return result
    except Exception as e:
        stream_custom_event("error", "some_node", {"error": str(e)})
        raise
```

---

## Migration Notes

### Before Migration

- Events were emitted in various formats
- Auto-wrapping logic in `entrypoint.py` created duplicate events
- No standardized format

### After Migration

- All events use standardized envelope format
- Single source of truth - events emitted once from nodes
- No duplication - auto-wrapping removed
- Centralized streaming functions ensure consistency

### Backward Compatibility

The `normalize_event()` function in `event_processor.py` handles old-format events during migration. All events are normalized to envelope format before being sent to the frontend.

---

## Best Practices

1. **Always use streaming functions** - Don't call `get_stream_writer()` directly
2. **Stream immediately** - Emit events right after they occur
3. **Use appropriate event types** - Choose `trace`, `custom`, or `state_update` based on event nature
4. **Include relevant data** - Put all event-specific data in the payload
5. **Handle errors** - Always stream error events in exception handlers
6. **Don't duplicate** - Events are emitted once from nodes, no need to wrap them elsewhere

---

## Questions?

If you're unsure about:
- **Which function to use?** → Use `stream_trace_event()` for trace events, `stream_custom_event()` for custom events
- **When to stream?** → Stream immediately after the event occurs
- **What format?** → Use the standardized envelope format (handled automatically by streaming functions)
- **Where to stream?** → From nodes directly, using streaming functions
