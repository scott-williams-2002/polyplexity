export interface ReferenceSource {
  id: string;
  title: string;
  url: string;
  domain: string;
  favicon?: string;
}

export type MessageRole = 'user' | 'assistant';

export type StreamStage = 'idle' | 'searching' | 'reasoning' | 'answering' | 'completed';

export interface Message {
  id: string;
  role: MessageRole;
  content: string; // The final answer or current stream
  reasoning?: string; // The "thought process" content
  sources?: ReferenceSource[];
  timestamp: number;
  
  // State for UI only (not necessarily persisted)
  stage?: StreamStage;
  isStreaming?: boolean;
  finalReportComplete?: boolean; // Track if final_report_complete event was received
}

export interface ChatState {
  messages: Message[];
  isGenerating: boolean;
}

export interface ThreadInfo {
  thread_id: string;
  name: string | null;
  last_message: string | null;
  updated_at: string | null;
  message_count: number;
}

export interface SSEEvent {
  // New standardized envelope format (per STREAM_RULES.md)
  type?: "trace" | "custom" | "state_update" | "system" | "error" | "complete" | "update";
  timestamp?: number;
  node?: string;
  event?: string;
  payload?: any; // Event-specific data dictionary
  
  // Backward compatibility fields (for transition period)
  content?: string;
  thought?: string;
  tool?: string;
  input?: any;
  error?: string;
  data?: any;
  response?: string;
  thread_id?: string;
  // Research agent specific events (legacy flat format)
  decision?: "research" | "finish";
  reasoning?: string;
  topic?: string;
  queries?: string[];
  query?: string;
  report?: string;
  summary?: string;
  name?: string;
  url?: string;
  markdown?: string;
}

export interface ExecutionTraceEvent {
  type: "node_call" | "reasoning" | "search" | "state_update" | "custom";
  node: string;
  timestamp: number;
  data: {
    event?: string;
    decision?: string;
    reasoning?: string;
    topic?: string;
    queries?: string[];
    query?: string;
    results?: Array<{title: string; url: string}>;
    update?: string;
    count?: number;
    value?: number;
    report?: string;
    url?: string;
    markdown?: string;
    [key: string]: any;
  };
}

// API Message format (from backend)
export interface ApiMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string | null;
  execution_trace?: ExecutionTraceEvent[];
}

// Source format from API (web_search_url events)
export interface Source {
  url: string;
  markdown: string;
}