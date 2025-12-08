# Frontend Rules

**Purpose**: This file documents debugging fixes that worked, to avoid repeating the same issues.

## Message Duplication When Switching Threads

### Issue
When switching between conversation threads, the conversation history was being duplicated in the UI. The problem occurred because:

1. **State not cleared before loading**: When switching threads, the frontend state still contained messages from the previous thread
2. **Appending instead of replacing**: History was being appended to existing messages instead of replacing them
3. **Race condition**: `setMessages([])` is async, so checking `messages.length === 0` immediately after clearing could still see old messages

### Root Cause
- Using `setMessages([...prev, ...formattedMessages])` or checking `messages.length` before loading caused appending instead of replacing
- React state updates are asynchronous, so checking state immediately after updating doesn't reflect the new value

### Fix / Rule
**Always use functional updates when replacing messages from thread history:**

```typescript
// ✅ CORRECT: Replace all messages, ignoring current state
setMessages(() => formattedMessages)

// ❌ WRONG: Appends to existing messages
setMessages((prev) => [...prev, ...formattedMessages])

// ❌ WRONG: May append if state hasn't updated yet
if (messages.length === 0) {
  setMessages(formattedMessages)
}
```

**When switching threads:**
1. Immediately clear messages: `setMessages([])`
2. Reset loaded thread ref: `loadedThreadIdRef.current = null`
3. Load history and use functional update to replace: `setMessages(() => formattedMessages)`
4. Never check `messages.length` to decide whether to load - use `loadedThreadIdRef` instead

