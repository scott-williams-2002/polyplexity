# Backend Rules

**Purpose**: This file documents debugging fixes that worked, to avoid repeating the same issues.

## Conversation History Duplication with operator.add

### Issue
Conversation history was being duplicated in the database when sending messages in existing threads. The problem occurred because:

1. **operator.add accumulation**: The `conversation_history` field uses `Annotated[List[str], operator.add]`, which means LangGraph **adds** returned values to existing state, not replaces them
2. **Including history in initial_state**: When initializing `initial_state` for follow-up conversations, we were copying existing `conversation_history` into the initial state
3. **Double accumulation**: LangGraph would then add the new messages to what was already in `initial_state`, causing duplication

### Root Cause
```python
# ❌ WRONG: Includes conversation_history in initial_state
if is_follow_up and existing_state:
    initial_state = {
        "user_message": message,
        "conversation_history": existing_history.copy(),  # This causes duplication!
        "final_response": existing_state.get("final_response", "")
    }
```

When `agent_node` returns `{"conversation_history": conversation_updates}`, LangGraph adds it to what's in `initial_state` (which already has the history), causing duplication.

### Fix / Rule
**Never include `conversation_history` in `initial_state` when using `operator.add`:**

```python
# ✅ CORRECT: Start with empty list, agent_node reads from checkpointer state
if is_follow_up and existing_state:
    initial_state = {
        "user_message": message,
        "conversation_history": [],  # Empty - agent_node reads from checkpointer
        "final_response": existing_state.get("final_response", "")
    }
```

**How it works:**
- `agent_node` reads history via `state.get("conversation_history", [])` which gets persisted state from checkpointer
- When `agent_node` returns `{"conversation_history": conversation_updates}`, LangGraph adds only the new messages to the persisted state
- No duplication because `initial_state` doesn't include existing history

**Key principle**: With `operator.add`, only return **new** values. Let LangGraph merge them with persisted state from the checkpointer.

---

## SSE Streaming Architecture

### Overview
The backend uses Server-Sent Events (SSE) to stream real-time updates to the frontend during agent execution. This enables live progress indicators, incremental content updates, and execution trace streaming.

### Implementation Pattern
```python
@app.post("/chat")
async def chat_agent(request: QueryRequest, thread_id: Optional[str] = None):
    async def sse_generator():
        for mode, data in run_research_agent(request.query, thread_id=thread_id):
            if mode == "custom":
                # Custom events: supervisor_decision, generated_queries, trace, etc.
                event_data = json.dumps(data)
                yield f"data: {event_data}\n\n"
            elif mode == "updates":
                # State updates: incremental content, node outputs
                for node_name, node_data in data.items():
                    update_data = {
                        "type": "update",
                        "node": node_name,
                        "data": node_data
                    }
                    yield f"data: {json.dumps(update_data)}\n\n"
    
    return StreamingResponse(sse_generator(), media_type="text/event-stream")
```

### Event Types
1. **Custom Events**: Emitted via `writer()` in nodes
   - `thread_id`: New thread ID when conversation starts
   - `thread_name`: Generated thread name (5 words or less)
   - `supervisor_decision`: Decision to research or finish
   - `generated_queries`: List of search queries
   - `search_start`: Individual search query being executed
   - `research_synthesis_done`: Research synthesis complete
   - `writing_report`: Final report generation started
   - `final_report_complete`: Final report ready
   - `trace`: Execution trace events (node calls, reasoning, etc.)

2. **Update Events**: State changes from nodes
   - `final_report`: Incremental report content (streams token-by-token)
   - `research_notes`: Accumulated research notes
   - `iterations`: Current iteration count

### Rules
- **Always yield events immediately**: Don't buffer events - frontend needs real-time updates
- **Use `writer()` for custom events**: Nodes should use `get_stream_writer()` to emit events
- **Include thread_id in initial events**: Frontend needs thread_id to manage state
- **Complete event**: Always send `{"type": "complete", "response": final_content}` at the end

---

## Hybrid State Persistence Architecture

### Overview
We use a **hybrid persistence approach** combining LangGraph's internal checkpointer with custom PostgreSQL tables for UI-friendly data retrieval.

### Two-Layer System

**Layer 1: LangGraph Checkpointer (PostgresSaver)**
- Stores agent state: `research_notes`, `iterations`, `conversation_history`, `final_report`
- Used by LangGraph for graph execution and state management
- Not optimized for UI queries (complex nested structure)

**Layer 2: Custom Message Store (PostgreSQL Tables)**
- `messages` table: User and assistant messages with `thread_id`, `role`, `content`, `message_index`
- `execution_traces` table: Execution trace events linked to messages via `message_id`
- `threads` table: Thread metadata including generated names
- Optimized for UI: Simple queries, fast retrieval, proper ordering

### Why Hybrid?
- **LangGraph state**: Complex nested state needed for agent execution
- **Message store**: Simple, flat structure for UI display
- **Separation of concerns**: Agent logic vs. UI presentation

### Implementation Pattern
```python
# In final_report_node:
# 1. Store messages in message_store (for UI)
user_message_id = save_message(thread_id, "user", user_request)
assistant_message_id = save_message(thread_id, "assistant", final_report)

# 2. Store execution trace (for UI)
for trace_event in full_execution_trace:
    save_execution_trace(assistant_message_id, event_type, event_data, ...)

# 3. Still update LangGraph state (for agent context)
return {
    "conversation_history": [user_msg, assistant_msg],
    "final_report": final_report,
    ...
}
```

### Rules
- **Always store in both places**: Messages go to `message_store` AND `conversation_history` in state
- **UI reads from message_store**: Frontend queries `/threads/{thread_id}/history` which reads from `messages` table
- **Agent reads from state**: Follow-up questions use `conversation_history` from LangGraph checkpointer
- **Thread names**: Stored in `threads` table, generated on first message via LLM

---

## Execution Trace Persistence

### Issue
Execution traces were being persisted incorrectly - only final_report events were stored, missing all earlier events (supervisor decisions, reasoning, searches, etc.).

### Root Cause
1. **`update_state()` doesn't work during streaming**: When we called `main_graph.update_state()` to set `_question_execution_trace` during streaming, nodes couldn't see the update
2. **final_report_node stored incomplete trace**: It only had access to its own events, not the full question trace
3. **Trace events collected but not persisted**: Events were streamed to frontend correctly but lost when saving

### Solution Pattern
```python
# 1. Collect ALL trace events during streaming
question_execution_trace = []
for mode, data in main_graph.stream(...):
    if mode == "custom" and data.get("event") == "trace":
        question_execution_trace.append(trace_event)
    
    # Also collect from state updates
    if mode == "updates" and node_name == "final_report":
        question_execution_trace.extend(node_data.get("execution_trace", []))

# 2. After graph completes, check if trace is incomplete
existing_traces = get_message_traces(assistant_message_id)
if len(existing_traces) < len(question_execution_trace):
    # 3. Delete incomplete trace
    delete_message_traces(assistant_message_id)
    
    # 4. Save complete trace
    for idx, trace_event in enumerate(question_execution_trace):
        save_execution_trace(assistant_message_id, ...)
```

### Rules
- **Never rely on `update_state()` during streaming**: Nodes won't see state updates made while graph is running
- **Collect trace events in `research_agent.py`**: Maintain `question_execution_trace` list during entire stream
- **Fix trace after completion**: Check trace completeness after graph finishes and replace if needed
- **Include final_report events**: Collect `execution_trace` from `final_report` node updates and add to collection
- **One trace per message**: Each assistant message has its own execution trace, reset per question

### Trace Event Structure
```python
{
    "type": "node_call" | "reasoning" | "search" | "state_update" | "custom",
    "node": "supervisor" | "call_researcher" | "final_report" | ...,
    "timestamp": int,  # Milliseconds since epoch
    "data": {
        "event": "supervisor_decision" | "generated_queries" | ...,
        "reasoning": str,  # For reasoning events
        "query": str,  # For search events
        "results": [...],  # For search results
        ...
    }
}
```

---

## Thread Name Generation

### Overview
Thread names are generated automatically on the first message using a lightweight LLM call. Names are limited to 5 words and stored in the `threads` table.

### Implementation Pattern
```python
# In supervisor_node (first iteration only):
if iteration == 0:
    thread_name = generate_thread_name(user_request)
    save_thread_name(thread_id, thread_name)
    writer({"event": "thread_name", "thread_id": thread_id, "name": thread_name})
```

### Generation Function
- **Model**: `llama-3.1-8b-instant` (lightweight, fast)
- **Temperature**: 0.3 (balanced creativity/consistency)
- **Prompt**: "Create a concise thread title (exactly 5 words or less) for this user query: {query}"
- **Fallback**: First 5 words of query if LLM fails

### Rules
- **Generate only on first message**: Check `iteration == 0` in supervisor_node
- **Emit SSE event**: Frontend needs `thread_name` event to update sidebar
- **Store in database**: Use `save_thread_name()` to persist in `threads` table
- **Handle failures gracefully**: Always have fallback to truncated query
- **5 words max**: Enforce length limit in generation function

