# Frontend Structure Overview

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Folder Structure Overview](#2-folder-structure-overview)
3. [SSE Streaming System](#3-sse-streaming-system)
4. [Persisted Log Parsing](#4-persisted-log-parsing)
5. [Charting System](#5-charting-system)
6. [Layout and Styling](#6-layout-and-styling)
7. [Polymarket API Reverse Engineering](#7-polymarket-api-reverse-engineering)
8. [Component Details](#8-component-details)

---

## 1. High-Level Architecture

The frontend is a **React + TypeScript + Vite** application built with a component-based architecture. The application follows a unidirectional data flow pattern where:

- **Data Flow**: SSE → hooks → components → UI
- **State Management**: React hooks (useState, useCallback, useEffect, useRef)
- **Build Tool**: Vite with React plugin
- **Styling**: Tailwind CSS via CDN with custom CSS variables
- **Dependencies**: Managed via ES modules and import maps (no bundler for dependencies)

### Key Architectural Patterns

1. **Custom Hooks Pattern**: Business logic is encapsulated in custom hooks (`useChatStream`, `useThreads`)
2. **Adapter Pattern**: Conversion between API formats and frontend types (`lib/adapters.ts`)
3. **Service Layer**: External API integrations isolated in `services/` directory
4. **Component Composition**: UI broken down into reusable, focused components

---

## 2. Folder Structure Overview

```
polyplexity/frontend/
├── App.tsx                 # Main application component with layout
├── index.tsx               # React entry point
├── index.html              # HTML entry point with Tailwind config
├── vite.config.ts          # Vite build configuration
├── types.ts                # TypeScript type definitions
├── components/             # React components
│   ├── ChatInterface.tsx   # Message list rendering
│   ├── MessageBubble.tsx   # Individual message display
│   ├── InputArea.tsx       # Chat input with send button
│   ├── PolymarketGraph.tsx # Price history chart component
│   ├── MarketChartsContainer.tsx # Container for multiple charts
│   ├── ReasoningAccordion.tsx   # Collapsible reasoning display
│   ├── SourcesGrid.tsx     # Grid of source cards
│   └── ui/
│       └── Icons.tsx       # Icon components
├── hooks/                  # Custom React hooks
│   ├── useChatStream.ts    # SSE streaming and event processing
│   └── useThreads.ts       # Thread list management
├── lib/                    # Utility libraries
│   ├── adapters.ts         # Type converters (API ↔ frontend)
│   ├── api.ts              # Backend API client (SSE, threads, history)
│   ├── utils.ts            # Utility functions (ID generation, class merging)
│   └── mockService.ts      # Mock services for development
└── services/               # External service integrations
    └── polymarketService.ts # Polymarket API client
```

---

## 3. SSE Streaming System

The SSE (Server-Sent Events) streaming system is the core mechanism for real-time updates from the backend. It's implemented in `hooks/useChatStream.ts`.

### 3.1 Event Normalization

The `normalizeToExecutionTraceEvent()` function converts SSE events from the backend into a standardized `ExecutionTraceEvent` format. This handles two different event formats:

#### Envelope Format (from streaming)
```typescript
{
  type: "trace" | "custom" | "state_update" | "system",
  node: string,
  event: string,
  payload: {
    type?: string,
    node?: string,
    timestamp?: number,
    data?: any,
    // ... event-specific fields
  },
  timestamp?: number
}
```

#### Direct Format (from persisted logs)
```typescript
{
  type: "node_call" | "reasoning" | "search" | "state_update" | "custom",
  node: string,
  timestamp: number,
  data: {
    event?: string,
    reasoning?: string,
    // ... event-specific fields
  }
}
```

**Normalization Process:**
1. Detects format by checking for `payload` property (envelope) vs `data` property (direct)
2. Extracts trace type from `payload.type` or infers from `event` name
3. Flattens nested structure into unified `ExecutionTraceEvent` format
4. Preserves event metadata (node, timestamp, event name)

### 3.2 Event Processing

The `handleEvent()` callback processes incoming SSE events and updates UI state accordingly:

#### Event Type Handling

**System Events:**
- `thread_id`: Updates thread ID, triggers thread change callback
- `thread_name`: Triggers message sent callback (for thread list refresh)

**Supervisor Decision Events:**
- `supervisor_decision`: Updates stage to "searching" or "answering" based on decision
- Extracts topic and reasoning for status display

**Research Events:**
- `generated_queries`: Updates status with query count
- `search_start`: Updates status with search query
- `web_search_url`: Adds source to sources array, updates status
- `research_synthesis_done`: Updates stage to "reasoning"

**Market Research Events:**
- `market_research_start`: Updates stage to "searching"
- `tag_selected`: Updates status with tag count
- `market_approved`: Updates status with market question
- `market_research_complete`: Updates stage to "answering"
- `polymarket_blurb_generated`: Updates stage to "answering"

**State Update Events:**
- `state_update` with `node === "call_market_research"`: Extracts `approved_markets` array
- `state_update` with `node === "rewrite_polymarket_response"`: Extracts `polymarket_blurb` string
- `state_update` with `final_report`: Updates streaming content and stage

**Completion Events:**
- `final_report_complete`: Sets stage to "completed", marks final report complete
- `complete`: Sets stage to "completed", finalizes content

### 3.3 State Management

The hook manages multiple pieces of state:

**Streaming State:**
- `isStreaming`: Boolean flag indicating active stream
- `streamingContent`: Accumulated content from stream
- `executionTrace`: Array of normalized `ExecutionTraceEvent` objects

**UI Stage Tracking:**
- `stage`: Current UI stage (`"idle" | "searching" | "reasoning" | "answering" | "completed"`)
- `currentStatus`: Human-readable status message
- `finalReportComplete`: Flag indicating final report event received

**Data State:**
- `sources`: Array of `Source` objects from search results
- `approvedMarkets`: Array of `ApprovedMarket` objects from market research
- `polymarketBlurb`: String containing market recommendations

**Thread Persistence:**
- Uses `useRef` to store `approvedMarkets` and `polymarketBlurb` for thread persistence
- Refs prevent loss of data during re-renders

**Reasoning Conversion:**
- `reasoning`: Computed string from `executionTraceToReasoning(executionTrace)`
- Converts execution trace events into formatted markdown reasoning text

### 3.4 Stream Lifecycle

1. **Start**: `startStreaming()` resets all state, calls `streamChat()` API
2. **During Stream**: Events processed via `handleEvent()`, state updated incrementally
3. **Completion**: `isStreaming` set to false, `stage` set to "completed"
4. **Reset**: `reset()` clears all streaming state

---

## 4. Persisted Log Parsing

When loading thread history, persisted execution traces must be converted to frontend message format. This happens in `App.tsx` and `lib/adapters.ts`.

### 4.1 Thread History Loading

**Location**: `App.tsx` useEffect hook (lines 42-74)

**Process:**
1. `getThreadHistory(threadId)` fetches `ApiMessage[]` from backend
2. Each `ApiMessage` contains:
   - `role`: "user" | "assistant"
   - `content`: Message text
   - `timestamp`: ISO string
   - `execution_trace`: Array of `ExecutionTraceEvent` objects

**Loading Trigger:**
- Triggered when `threadId` changes
- Uses `loadedThreadIdRef` to prevent duplicate loads
- Clears messages when threadId is null

### 4.2 Message Conversion

The `apiMessageToViteMessage()` function converts API format to frontend `Message` format:

**Conversion Steps:**

1. **Reasoning Extraction:**
   ```typescript
   const reasoning = executionTraceToReasoning(msg.execution_trace)
   ```
   - Converts execution trace events to formatted markdown string
   - Filters out market data and blurb (displayed separately)

2. **Sources Extraction:**
   - Parses markdown links from reasoning text: `parseMarkdownLinks(reasoning)`
   - Extracts search result links from trace: `extractSearchLinksFromTrace(execution_trace)`
   - Merges and deduplicates by URL

3. **Market Data Extraction:**
   - `extractApprovedMarketsFromTrace()`: Finds latest `state_update` from `call_market_research` node
   - `extractPolymarketBlurbFromTrace()`: Finds latest `state_update` from `rewrite_polymarket_response` node

4. **Message Construction:**
   - Creates `Message` object with all extracted data
   - Sets `stage: "completed"` and `isStreaming: false` for persisted messages
   - Generates stable ID or uses provided ID

### 4.3 Trace Event Processing

**ExecutionTraceEvent Format:**
```typescript
{
  type: "node_call" | "reasoning" | "search" | "state_update" | "custom",
  node: string,
  timestamp: number,
  data: {
    event?: string,
    reasoning?: string,
    approved_markets?: ApprovedMarket[],
    polymarket_blurb?: string,
    results?: Array<{title: string; url: string}>,
    // ... other event-specific fields
  }
}
```

**Event Type Handling:**

- **`reasoning`**: Contains markdown-formatted thought process
- **`search`**: Contains search results with URLs
- **`state_update`**: Contains state changes (approved_markets, polymarket_blurb)
- **`node_call`**: Node execution metadata (typically not displayed)
- **`custom`**: Custom events (supervisor_decision, generated_queries, etc.)

**Reasoning Conversion Logic:**

The `executionTraceToReasoning()` function:
- Iterates through execution trace events
- Extracts reasoning text from `reasoning` type events
- Formats custom events (supervisor_decision, search_start, etc.) as markdown
- Skips state_update events containing market data (displayed separately)
- Joins all reasoning parts with double newlines

**Source Extraction Logic:**

The `extractSearchLinksFromTrace()` function:
- Searches for `search` type events with `results` array
- Extracts URLs and titles from search results
- Converts to `ReferenceSource` format with stable IDs
- Deduplicates by URL

---

## 5. Charting System

The charting system displays Polymarket price history using Recharts. Implemented in `components/PolymarketGraph.tsx`.

### 5.1 Chart Architecture

**Library**: Recharts (`AreaChart`, `Area`, `XAxis`, `YAxis`, `Tooltip`, `ResponsiveContainer`)

**Layout:**
- Fixed height container: 350px
- Side-by-side layout: 70% chart area, 30% sidebar
- Responsive container handles width adjustments

**Chart Type**: Multi-line area chart showing price history for multiple outcomes

### 5.2 Data Fetching

**Function**: `fetchPriceHistory()` in `services/polymarketService.ts`

**Retry Logic:**
1. **First Attempt**: `interval=max` (no fidelity parameter)
   - Returns all available data points
   - Most efficient for markets with limited history

2. **Second Attempt** (if first returns empty): `interval=all` with `fidelity=60`
   - Returns data points at 60-second intervals
   - Handles markets that don't support `max` interval

**Parallel Fetching:**
- All `clobTokenIds` fetched in parallel using `Promise.all()`
- Each token handled independently (errors don't block others)
- Empty data arrays returned for failed tokens

**Error Handling:**
- Failed tokens logged but don't crash component
- Empty data arrays filtered out before rendering
- Error state displayed if all tokens fail

### 5.3 Data Processing

**Combining Data Points:**

1. **Timestamp Collection:**
   - Collects all unique timestamps from all token data
   - Creates sorted array of timestamps

2. **Data Point Creation:**
   - For each timestamp, creates data point: `{t: timestamp, [clobTokenId]: price}`
   - Looks for exact timestamp match first
   - If no match, performs linear interpolation

3. **Linear Interpolation:**
   - Finds closest point before and after timestamp
   - Calculates ratio: `(timestamp - before.t) / (after.t - before.t)`
   - Interpolates price: `before.p + (after.p - before.p) * ratio`
   - Handles edge cases (only before or only after point)

4. **Sorting:**
   - Data sorted chronologically by timestamp
   - Ensures chart displays correctly

**Chart Data Structure:**
```typescript
[
  { t: 1234567890, "token1": 0.45, "token2": 0.55 },
  { t: 1234567900, "token1": 0.46, "token2": 0.54 },
  // ...
]
```

### 5.4 Chart Features

**Color Coding:**
- Each outcome assigned color from `LINE_COLORS` palette
- Colors cycle if more outcomes than colors
- Gradient fills use same color with opacity

**Hover Interactions:**
- `onMouseMove` handler detects hovered token
- Updates `hoveredClobTokenId` and `hoveredPrice` state
- Highlights corresponding line (thicker stroke, higher opacity)
- Scrolls sidebar to show hovered outcome
- Custom tooltip hidden (uses custom hover handling)

**Click Selection:**
- Click outcome in sidebar to select/deselect
- Selected outcome highlighted (same as hovered)
- Clicking selected outcome deselects it

**Visual Effects:**
- Gradient fills under area charts
- Drop shadow on active lines
- Smooth transitions on hover/select
- Custom cursor styling

**Y-Axis Domain:**
- Calculates min/max from all prices
- Adds 15% padding above and below
- Clamps to [0, 1] range (price is 0-1 normalized)

**X-Axis Formatting:**
- Formats timestamps as "MMM d" (e.g., "Jan 15")
- Uses `date-fns` format function
- Custom tick styling (gray, small font)

### 5.5 Polymarket API Integration

**Endpoint**: `https://clob.polymarket.com/prices-history`

**Parameters:**
- `market` (required): clobTokenId string
- `interval` (required): "max" or "all"
- `fidelity` (optional): Number in seconds (for "all" interval)

**Response Format:**
```typescript
{
  history: [
    { t: 1234567890, p: 0.45 }, // Unix timestamp, price (0-1)
    // ...
  ]
}
```

**API Discovery:**
- Reverse engineered from Polymarket frontend network requests
- Public endpoint (no authentication required)
- Discovered by inspecting browser DevTools Network tab

**Behavior:**
- `interval=max`: Returns all available data (no fidelity needed)
- `interval=all` with `fidelity`: Returns data at specified interval
- Common fidelity values: 10, 30, 60, 120, 720 (seconds)
- Some markets return empty data with certain parameters
- Retry logic handles empty responses gracefully

---

## 6. Layout and Styling

### 6.1 Design System

**Location**: `index.html` (lines 48-91)

**Tailwind CSS:**
- Loaded via CDN: `https://cdn.tailwindcss.com`
- Custom configuration in `<script>` tag
- Extended theme with custom colors and fonts

**CSS Variables (HSL Color System):**
```css
:root {
  --primary: 271 81% 56%;        /* Purple primary color */
  --foreground: 240 10% 3.9%;     /* Text color */
  --background: 0 0% 100%;        /* Background color */
  --muted: 240 4.8% 95.9%;        /* Muted backgrounds */
  --border: 240 5.9% 90%;         /* Border color */
  /* ... */
}
```

**Typography:**
- Font family: Inter (Google Fonts)
- Font weights: 300, 400, 500, 600, 700
- Applied globally via `body` selector

**Custom Scrollbar:**
- Webkit scrollbar styling
- 8px width/height
- Gray thumb with hover effect
- Transparent track

### 6.2 Component Layout

**Main Layout** (`App.tsx`):

**Desktop:**
- Sidebar (left): 256px width (`w-64`)
  - Logo and branding
  - "New Thread" button
  - Thread list ("Library")
  - User profile footer
- Main content (right): Flex-1 (remaining space)
  - Chat interface (scrollable)
  - Input area (sticky bottom)

**Mobile:**
- Sidebar hidden (`hidden md:flex`)
- Header bar (mobile only): Logo and branding
- Main content: Full width

**Sticky Elements:**
- Input area: Sticky bottom (`sticky bottom-0`)
- Message reasoning/sources: Sticky top during streaming

### 6.3 Message Bubble Layout

**Vertical Stack** (`MessageBubble.tsx`):

1. **Header Section** (sticky during streaming):
   - Reasoning accordion (collapsible)
   - Sources grid

2. **Content Section** (scrollable):
   - Markdown-rendered content
   - Auto-scrolls during streaming

3. **Polymarket Blurb**:
   - Purple-bordered box
   - Markdown-rendered text
   - Displayed above charts

4. **Market Charts**:
   - `MarketChartsContainer` component
   - Renders `PolymarketGraph` for each approved market

**Sticky Behavior:**
- Header sticky when: `stage !== 'completed' && isStreaming !== false && finalReportComplete !== true`
- Auto-collapses reasoning when `stage === 'answering'`
- Keeps reasoning open during `stage === 'reasoning'`

**Loading States:**
- Purple loading indicators while waiting for Polymarket data
- Rotating loading messages every 2 seconds
- Detected when: `finalReportComplete && !polymarketBlurb && !approvedMarkets`

### 6.4 Styling Approach

**Tailwind Utility Classes:**
- Extensive use of utility classes for styling
- No separate CSS files (except inline styles in `index.html`)
- Utility-first approach

**CSS Variables:**
- Theme colors accessed via `hsl(var(--primary))`
- Consistent color system throughout
- Easy theme customization

**Glassmorphism Effects:**
- `backdrop-blur-sm` for sticky headers
- `bg-background/95` for semi-transparent backgrounds
- Creates depth and layering

**Rounded Corners:**
- `rounded-xl`: 12px radius (cards, containers)
- `rounded-2xl`: 16px radius (message bubbles, buttons)
- `rounded-full`: Circular (buttons, avatars)

**Transitions:**
- `transition-colors`: Smooth color changes
- `transition-all`: Multi-property transitions
- `duration-300`: 300ms transition duration
- `ease-out`: Easing function

**Purple Accent Color:**
- Primary color: `271 81% 56%` (purple)
- Used for:
  - Primary buttons
  - Links
  - Loading indicators
  - Polymarket blurb borders
  - Branding ("Poly" text)

---

## 7. Polymarket API Reverse Engineering

### 7.1 Price History Endpoint

**Discovery Process:**
- Inspected Polymarket frontend network requests in browser DevTools
- Identified endpoint: `https://clob.polymarket.com/prices-history`
- Analyzed request parameters and response format

**Endpoint Details:**
- **URL**: `https://clob.polymarket.com/prices-history`
- **Method**: GET
- **Authentication**: None required (public endpoint)
- **CORS**: Allowed (can be called from browser)

**Parameters:**
- `market` (required): clobTokenId string
  - Example: `"0x1234...abcd"`
  - Identifies specific market outcome token
- `interval` (required): "max" or "all"
  - `"max"`: Returns all available data (most efficient)
  - `"all"`: Returns data with optional fidelity parameter
- `fidelity` (optional): Number in seconds
  - Only used with `interval=all`
  - Common values: 10, 30, 60, 120, 720
  - Determines data point interval

### 7.2 API Behavior

**Interval="max":**
- Returns all available historical data
- No fidelity parameter needed
- Most efficient (single request, all data)
- Some markets may return empty data

**Interval="all" with Fidelity:**
- Returns data points at specified interval
- Example: `fidelity=60` returns one point per minute
- Useful when `max` returns empty data
- More data points = more requests (if needed)

**Error Handling:**
- Empty `history` array: Market may not support parameters
- HTTP errors: Standard error responses
- Network errors: Caught and handled gracefully

**Retry Strategy:**
1. Try `interval=max` first (most efficient)
2. If empty, try `interval=all` with `fidelity=60`
3. If both fail, throw error

### 7.3 Data Format

**Response Structure:**
```typescript
{
  history: [
    { t: 1234567890, p: 0.45 },
    { t: 1234567900, p: 0.46 },
    // ...
  ]
}
```

**Field Descriptions:**
- `t`: Unix timestamp in seconds (not milliseconds)
- `p`: Price normalized to 0-1 range (multiply by 100 for percentage)

**Data Characteristics:**
- Timestamps may not be evenly spaced
- Some timestamps may be missing for certain tokens
- Prices are floating-point numbers (0.0 to 1.0)
- Array sorted chronologically (ascending)

**Usage in Frontend:**
- Timestamps converted to JavaScript Date: `new Date(timestamp * 1000)`
- Prices displayed as percentages: `(price * 100).toFixed(1) + "¢"`
- Linear interpolation fills gaps for smooth chart display

---

## 8. Component Details

### 8.1 Core Components

#### `App.tsx`
**Purpose**: Main application component with layout and state management

**Key Responsibilities:**
- Manages message list state
- Handles thread selection and loading
- Integrates `useChatStream` and `useThreads` hooks
- Converts persisted messages to frontend format
- Updates messages during streaming
- Renders sidebar and main content layout

**State Management:**
- `messages`: Array of `Message` objects
- `threadId`: Current thread ID (null for new threads)
- `refreshTrigger`: Counter to trigger thread list refresh

**Effects:**
- Loads thread history when `threadId` changes
- Updates messages during streaming
- Finalizes messages when streaming completes

#### `ChatInterface.tsx`
**Purpose**: Renders message list with auto-scroll

**Key Features:**
- Maps messages to `MessageBubble` components
- Auto-scrolls to bottom on content updates
- Empty state when no messages
- Spacer for sticky input area

**Props:**
- `messages`: Array of `Message` objects
- `isGenerating`: Boolean indicating active generation

#### `MessageBubble.tsx`
**Purpose**: Individual message display with reasoning, sources, content, and charts

**Layout Structure:**
1. Header (sticky during streaming):
   - Reasoning accordion
   - Sources grid
2. Content area (scrollable):
   - Markdown-rendered content
   - Auto-scroll during streaming
3. Polymarket blurb (if present)
4. Market charts container (if markets present)

**Features:**
- Auto-collapse reasoning when answering starts
- Sticky header during streaming
- Loading indicators for Polymarket data
- Markdown rendering with custom components

**Props:**
- `message`: `Message` object
- `isLast`: Boolean indicating last message

#### `InputArea.tsx`
**Purpose**: Chat input with send button

**Features:**
- Text input with placeholder
- Send button (disabled during streaming)
- Keyboard shortcut (Enter to send)
- Sticky positioning at bottom

#### `PolymarketGraph.tsx`
**Purpose**: Price history chart for single market

**Features:**
- Multi-line area chart (Recharts)
- Side-by-side layout (70% chart, 30% sidebar)
- Hover interactions
- Click selection
- Market description dropdown
- Refresh button
- Current price display

**Props:**
- `market`: `ApprovedMarket` object

#### `MarketChartsContainer.tsx`
**Purpose**: Container for multiple market charts

**Features:**
- Maps approved markets to `PolymarketGraph` components
- Handles loading states
- Error boundaries

**Props:**
- `markets`: Array of `ApprovedMarket` objects

#### `ReasoningAccordion.tsx`
**Purpose**: Collapsible reasoning display

**Features:**
- Expand/collapse toggle
- Markdown rendering
- Streaming indicator
- Auto-expand during reasoning stage

**Props:**
- `reasoning`: Markdown string
- `isOpen`: Boolean state
- `isStreaming`: Boolean indicating active stream
- `onToggle`: Toggle callback

#### `SourcesGrid.tsx`
**Purpose**: Grid of source cards

**Features:**
- Responsive grid layout
- Source cards with title, domain, URL
- External link icons
- Streaming indicator

**Props:**
- `sources`: Array of `ReferenceSource` objects
- `isStreaming`: Boolean indicating active stream

### 8.2 Hooks

#### `useChatStream.ts`
**Purpose**: SSE streaming and event processing

**Returns:**
- `isStreaming`: Boolean
- `streamingContent`: String
- `executionTrace`: Array of `ExecutionTraceEvent`
- `reasoning`: Computed string from trace
- `sources`: Array of `Source`
- `stage`: `StreamStage`
- `finalReportComplete`: Boolean
- `approvedMarkets`: Array of `ApprovedMarket`
- `polymarketBlurb`: String | null
- `startStreaming`: Function
- `reset`: Function

**Key Functions:**
- `normalizeToExecutionTraceEvent()`: Event normalization
- `handleEvent()`: Event processing
- `startStreaming()`: Start stream
- `reset()`: Reset state

#### `useThreads.ts`
**Purpose**: Thread list management

**Returns:**
- `threads`: Array of `ThreadInfo`
- `loading`: Boolean
- `deleteThread`: Function

**Features:**
- Fetches thread list from API
- Handles thread deletion
- Refreshes on trigger

### 8.3 Services

#### `polymarketService.ts`
**Purpose**: Polymarket API client

**Functions:**
- `fetchPriceHistory(clobTokenId)`: Fetches price history with retry logic

**Retry Logic:**
1. Try `interval=max`
2. If empty, try `interval=all` with `fidelity=60`
3. Throw error if both fail

#### `api.ts`
**Purpose**: Backend API client

**Functions:**
- `fetchThreads()`: Get thread list
- `streamChat()`: Start SSE stream
- `deleteThread()`: Delete thread
- `getThreadHistory()`: Get thread messages
- `healthCheck()`: Health check endpoint

**SSE Implementation:**
- Uses `fetch()` with `Accept: text/event-stream`
- Reads stream with `ReadableStream` API
- Parses SSE format (`data: {...}`)
- Calls `onEvent` callback for each event

### 8.4 Adapters (`lib/adapters.ts`)

**Purpose**: Convert between API and frontend types

**Functions:**
- `executionTraceToReasoning()`: Converts trace to markdown reasoning
- `sourceToReferenceSource()`: Converts `Source` to `ReferenceSource`
- `parseMarkdownLinks()`: Parses markdown links from text
- `extractApprovedMarketsFromTrace()`: Extracts markets from trace
- `extractPolymarketBlurbFromTrace()`: Extracts blurb from trace
- `extractSearchLinksFromTrace()`: Extracts search URLs from trace
- `apiMessageToViteMessage()`: Converts `ApiMessage` to `Message`

**Key Patterns:**
- Stable ID generation for sources (prevents re-renders)
- Deduplication by URL
- Merging sources from multiple sources (reasoning + search results)
- Filtering market data from reasoning display

### 8.5 Utilities (`lib/utils.ts`)

**Functions:**
- `cn()`: Merges Tailwind classes (clsx + tailwind-merge)
- `generateId()`: Random ID generator
- `generateStableId()`: Deterministic ID from string (hash-based)
- `delay()`: Promise-based delay (for mocking)

---

## Data Flow Diagrams

### Streaming Flow

```
User Input
    ↓
App.tsx: handleSendMessage()
    ↓
useChatStream: startStreaming()
    ↓
api.ts: streamChat() → SSE Connection
    ↓
Backend sends SSE events
    ↓
api.ts: onEvent() callback
    ↓
useChatStream: handleEvent()
    ↓
normalizeToExecutionTraceEvent()
    ↓
Update state (executionTrace, sources, stage, etc.)
    ↓
App.tsx: useEffect() updates messages
    ↓
ChatInterface renders MessageBubble
    ↓
UI updates
```

### Persisted Log Flow

```
User selects thread
    ↓
App.tsx: useEffect() detects threadId change
    ↓
api.ts: getThreadHistory(threadId)
    ↓
Backend returns ApiMessage[]
    ↓
adapters.ts: apiMessageToViteMessage()
    ↓
executionTraceToReasoning()
extractApprovedMarketsFromTrace()
extractPolymarketBlurbFromTrace()
extractSearchLinksFromTrace()
parseMarkdownLinks()
    ↓
App.tsx: setMessages(formattedMessages)
    ↓
ChatInterface renders MessageBubble
    ↓
UI displays persisted messages
```

### Chart Data Flow

```
MessageBubble renders MarketChartsContainer
    ↓
MarketChartsContainer maps markets to PolymarketGraph
    ↓
PolymarketGraph: useEffect() triggers loadData()
    ↓
polymarketService.ts: fetchPriceHistory() (parallel for all tokens)
    ↓
Polymarket API: prices-history endpoint
    ↓
Response: {history: [{t, p}]}
    ↓
PolymarketGraph: Process data (combine timestamps, interpolate)
    ↓
Recharts: Render AreaChart
    ↓
UI displays price history chart
```

---

## Code Examples

### Event Normalization Example

```typescript
// Envelope format (from streaming)
const envelopeEvent = {
  type: "trace",
  node: "call_researcher",
  event: "web_search_url",
  payload: {
    type: "custom",
    data: {
      url: "https://example.com",
      markdown: "[Example](https://example.com)"
    }
  },
  timestamp: 1234567890
};

// Normalized to ExecutionTraceEvent
const normalized = {
  type: "custom",
  node: "call_researcher",
  timestamp: 1234567890,
  data: {
    event: "web_search_url",
    url: "https://example.com",
    markdown: "[Example](https://example.com)"
  }
};
```

### Reasoning Conversion Example

```typescript
// Execution trace events
const events = [
  {
    type: "custom",
    node: "supervisor",
    timestamp: 1234567890,
    data: {
      event: "supervisor_decision",
      reasoning: "User wants to know about market trends"
    }
  },
  {
    type: "search",
    node: "call_researcher",
    timestamp: 1234567900,
    data: {
      query: "market trends 2024",
      results: [{title: "Article", url: "https://example.com"}]
    }
  }
];

// Converted to reasoning string
const reasoning = `> User wants to know about market trends

> Searching: market trends 2024`;
```

### Chart Data Processing Example

```typescript
// Token data (from API)
const tokenDataList = [
  {
    clobTokenId: "0x1234",
    data: [
      {t: 1000, p: 0.5},
      {t: 2000, p: 0.6}
    ]
  },
  {
    clobTokenId: "0x5678",
    data: [
      {t: 1500, p: 0.4},
      {t: 2500, p: 0.5}
    ]
  }
];

// Combined chart data
const chartData = [
  {t: 1000, "0x1234": 0.5},                    // Exact match
  {t: 1500, "0x1234": 0.55, "0x5678": 0.4},   // Interpolated + exact
  {t: 2000, "0x1234": 0.6},                    // Exact match
  {t: 2500, "0x1234": 0.6, "0x5678": 0.5}     // Extrapolated + exact
];
```

---

## Summary

This frontend architecture provides:

1. **Real-time Updates**: SSE streaming for live progress
2. **Persistence**: Thread history loading and display
3. **Rich Visualizations**: Polymarket price history charts
4. **Type Safety**: TypeScript throughout
5. **Modular Design**: Separated concerns (hooks, services, adapters)
6. **Responsive UI**: Mobile and desktop layouts
7. **Performance**: Parallel data fetching, efficient rendering

The system handles both streaming (real-time) and persisted (historical) data seamlessly, converting between formats automatically and maintaining a consistent UI experience.
