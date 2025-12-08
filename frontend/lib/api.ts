/**
 * API client for backend communication
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ThreadInfo {
  thread_id: string;
  name: string | null;
  last_message: string | null;
  updated_at: string | null;
  message_count: number;
}

export interface SSEEvent {
  event?: string;
  type?: string;
  content?: string;
  thought?: string;
  tool?: string;
  input?: any;
  error?: string;
  node?: string;
  data?: any;
  response?: string;
  thread_id?: string;
  timestamp?: number;
  // Research agent specific events
  decision?: "research" | "finish";
  reasoning?: string;
  topic?: string;
  queries?: string[];
  query?: string;
  report?: string;
  summary?: string;
  name?: string;
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
    [key: string]: any;
  };
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp?: string | null;
  execution_trace?: ExecutionTraceEvent[];
}

/**
 * Fetch all conversation threads
 */
export async function fetchThreads(): Promise<ThreadInfo[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/threads`);
    if (!response.ok) {
      throw new Error(`Failed to fetch threads: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching threads:', error);
    return [];
  }
}

/**
 * Stream chat messages from the backend using Server-Sent Events (SSE)
 */
export async function streamChat(
  message: string,
  threadId: string | null,
  onEvent: (event: SSEEvent) => void
): Promise<void> {
  const url = new URL(`${API_BASE_URL}/chat`);
  if (threadId) {
    url.searchParams.append('thread_id', threadId);
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query: message }),
  });

  if (!response.ok) {
    throw new Error(`Failed to stream chat: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('No response body reader available');
  }

  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    
    // Keep the last incomplete line in the buffer
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(data);
        } catch (error) {
          console.error('Error parsing SSE event:', error, line);
        }
      }
    }
  }

  // Process any remaining data in buffer
  if (buffer.trim()) {
    const lines = buffer.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent(data);
        } catch (error) {
          console.error('Error parsing SSE event:', error, line);
        }
      }
    }
  }
}

/**
 * Delete a conversation thread
 */
export async function deleteThread(threadId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/threads/${threadId}`, {
      method: 'DELETE',
    });
    
    // Check for success status codes (204 No Content or 200 OK)
    if (response.status === 204 || response.status === 200) {
      return true; // Success
    }
    
    if (response.status === 404) {
      throw new Error('Thread not found');
    }
    
    // Try to parse error response, but handle cases where JSON might not be available
    let errorMessage = `Failed to delete thread (status ${response.status})`;
    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          errorMessage = errorData.detail;
        }
      }
    } catch {
      // If JSON parsing fails, use the status code
      errorMessage = `Failed to delete thread (status ${response.status})`;
    }
    
    throw new Error(errorMessage);
  } catch (error) {
    console.error('Error deleting thread:', error);
    throw error;
  }
}

/**
 * Get conversation history for a thread
 */
export async function getThreadHistory(threadId: string): Promise<Message[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/threads/${threadId}/history`);
    
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Thread not found');
      }
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(errorData.detail || `Failed to fetch thread history: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching thread history:', error);
    throw error;
  }
}

/**
 * Health check endpoint
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
}

