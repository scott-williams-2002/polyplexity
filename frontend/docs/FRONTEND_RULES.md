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

---

## SSE Event Handling and Streaming

### Overview
The frontend receives real-time updates via Server-Sent Events (SSE) from the backend. Events include progress indicators, incremental content updates, execution traces, and thread management events.

### Event Handler Pattern
```typescript
await streamChat(userMessage.content, currentThreadId, (event: SSEEvent) => {
  // Handle different event types
  if (event.event === "thread_id") {
    // Update thread ID
  }
  if (event.event === "thread_name") {
    // Trigger sidebar refresh
  }
  if (event.type === "update" && event.node === "final_report") {
    // Incremental content updates
  }
  if (event.type === "complete") {
    // Finalize message
  }
})
```

### Event Types and Handling

1. **Thread Management Events**
   - `thread_id`: Update `currentThreadId` and call `onThreadIdChange()`
   - `thread_name`: Call `onMessageSent()` to trigger sidebar refresh (shows new name)

2. **Progress Events**
   - `supervisor_decision`: Update `progressMessage` based on decision
   - `generated_queries`: Show query count
   - `search_start`: Show current search query
   - `writing_report`: Show "Writing final report..."

3. **Content Updates**
   - `final_report_complete`: Set `streamingContent` to full report
   - `type: "update"` with `node: "final_report"`: Incrementally update `streamingContent`

4. **Execution Trace Events**
   - `event: "trace"`: Add to `executionTrace` state
   - `supervisor_decision`, `generated_queries`, etc.: Convert to `ExecutionTraceEvent` and add to trace

5. **Completion**
   - `type: "complete"`: Finalize message, clear streaming state, attach execution trace

### Rules
- **Always handle `thread_id` first**: Needed for thread management
- **Update `streamingContent` incrementally**: For `final_report` updates, append/update content
- **Convert events to trace format**: Many events need conversion to `ExecutionTraceEvent` structure
- **Clear state on completion**: Reset `isStreaming`, `streamingContent`, `executionTrace`, `progressMessage`
- **Trigger sidebar refresh**: Call `onMessageSent()` when `thread_name` received

---

## Execution Trace State Management

### Overview
Execution traces are collected during streaming and displayed in a collapsible section within chat messages. Traces show node calls, reasoning, searches, and state updates in chronological order.

### State Management Pattern
```typescript
const [executionTrace, setExecutionTrace] = useState<ExecutionTraceEvent[]>([])

// During streaming - add events as they arrive
if (event.event === "trace") {
  setExecutionTrace((prev) => [...prev, traceEvent])
}

// Convert other events to trace format
if (event.event === "supervisor_decision") {
  const traceEvent: ExecutionTraceEvent = {
    type: "custom",
    node: "supervisor",
    timestamp: Date.now(),
    data: { event: "supervisor_decision", decision: event.decision, ... }
  }
  setExecutionTrace((prev) => [...prev, traceEvent])
}

// On completion - attach to message
const assistantMessage = {
  ...,
  execution_trace: executionTrace.length > 0 ? [...executionTrace] : undefined
}

// Clear trace for next message
setExecutionTrace([])
```

### Trace Event Structure
```typescript
interface ExecutionTraceEvent {
  type: "node_call" | "reasoning" | "search" | "state_update" | "custom"
  node: string
  timestamp: number  // Milliseconds
  data: {
    event?: string
    reasoning?: string
    query?: string
    results?: Array<{title: string, url: string}>
    ...
  }
}
```

### Display Rules
- **Show trace even when content empty**: During streaming, trace may exist before final report
- **Auto-expand during streaming**: Keep trace visible while `isStreaming === true`
- **Auto-collapse on completion**: Collapse trace when streaming completes
- **Chronological ordering**: Sort events by `timestamp` before rendering
- **Format by type**: Node calls bold, reasoning indented, search results as links

### Rules
- **Always initialize trace**: Start with empty array `[]` for each new message
- **Update trace in real-time**: Add events as they stream in, not just at completion
- **Clear trace after completion**: Reset `executionTrace` to `[]` after attaching to message
- **Ensure trace updates trigger re-render**: Always set `execution_trace` on streaming message (even if empty) to trigger updates
- **Handle persisted traces**: When loading history, traces come from database, not streaming

---

## Thread Name Updates

### Overview
Thread names are generated on the backend and streamed to the frontend via SSE. The sidebar must refresh when a name is received to display the new name.

### Update Pattern
```typescript
// In SSE event handler
if (event.event === "thread_name" && event.name) {
  // Trigger sidebar refresh
  onMessageSent()
}

// In ThreadSidebar component
useEffect(() => {
  if (refreshTrigger > 0) {
    loadThreads()  // Reloads threads, including names
  }
}, [refreshTrigger, loadThreads])
```

### Rules
- **Listen for `thread_name` event**: Handle in SSE event callback
- **Trigger sidebar refresh**: Call `onMessageSent()` when name received (increments `refreshTrigger`)
- **Sidebar queries include names**: `/threads` endpoint returns thread names from `threads` table
- **Display fallback**: Show "New Chat" or truncated thread_id if name not available
- **Update happens automatically**: Sidebar refresh fetches latest thread data including names

