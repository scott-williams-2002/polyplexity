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

