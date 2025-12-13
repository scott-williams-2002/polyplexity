/**
 * API client for backend communication
 */
import { ThreadInfo, SSEEvent, ApiMessage } from "../types";
import { getApiKey } from "./auth";

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://freshair.dev/api';

/**
 * Get headers with Authorization Bearer token if API key exists
 */
function getHeaders(additionalHeaders: Record<string, string> = {}): HeadersInit {
  const headers: Record<string, string> = {
    ...additionalHeaders,
  };
  
  const apiKey = getApiKey();
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }
  
  return headers;
}

/**
 * Fetch all conversation threads
 */
export async function fetchThreads(): Promise<ThreadInfo[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/threads`, {
      headers: getHeaders(),
    });
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

  let response: Response;
  try {
    console.log('[SSE] Sending request to:', url.toString());
    response = await fetch(url.toString(), {
      method: 'POST',
      headers: getHeaders({
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      }),
      body: JSON.stringify({ query: message }),
    });
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Network error: Unable to connect to backend. Please ensure the backend server is running at ' + API_BASE_URL);
    }
    throw error;
  }

  if (!response.ok) {
    if (response.status === 500) {
      throw new Error('Server error: Please check if the backend is running correctly');
    }
    throw new Error(`Failed to stream chat: ${response.statusText}`);
  }

  console.log('[SSE] Response OK, Content-Type:', response.headers.get('content-type'));
  console.log('[SSE] Response status:', response.status);

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('No response body reader available');
  }

  let buffer = '';
  let chunkCount = 0;

  console.log('[SSE] Starting to read stream...');
  
  while (true) {
    const { done, value } = await reader.read();
    
    if (done) {
      console.log('[SSE] Stream reader done');
      break;
    }

    chunkCount++;
    const chunk = decoder.decode(value, { stream: true });
    console.log(`[SSE] Received chunk ${chunkCount}:`, chunk.substring(0, 200));
    
    buffer += chunk;
    const lines = buffer.split('\n');
    
    // Keep the last incomplete line in the buffer
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const rawJson = line.slice(6);
          console.log('[SSE] Raw JSON:', rawJson);
          const data = JSON.parse(rawJson);
          console.log('[SSE] Parsed event:', JSON.stringify(data, null, 2));
          onEvent(data);
        } catch (error) {
          console.error('Error parsing SSE event:', error, line);
        }
      } else if (line.trim() && !line.startsWith(':')) {
        // Log non-empty lines that aren't comments or data
        console.log('[SSE] Non-data line:', line);
      }
    }
  }

  // Process any remaining data in buffer
  if (buffer.trim()) {
    const lines = buffer.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const rawJson = line.slice(6);
          console.log('[SSE] Raw JSON (buffer):', rawJson);
          const data = JSON.parse(rawJson);
          console.log('[SSE] Parsed event (buffer):', JSON.stringify(data, null, 2));
          onEvent(data);
        } catch (error) {
          console.error('Error parsing SSE event:', error, line);
        }
      }
    }
  }
  
  console.log('[SSE] Stream completed');
}

/**
 * Delete a conversation thread
 */
export async function deleteThread(threadId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/threads/${threadId}`, {
      method: 'DELETE',
      headers: getHeaders(),
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
export async function getThreadHistory(threadId: string): Promise<ApiMessage[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/threads/${threadId}/history`, {
      headers: getHeaders(),
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Thread not found');
      }
      if (response.status === 500) {
        throw new Error('Server error: Please check if the backend is running');
      }
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(errorData.detail || `Failed to fetch thread history: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Network error: Unable to connect to backend. Please ensure the backend server is running.');
    }
    console.error('Error fetching thread history:', error);
    throw error;
  }
}

/**
 * Health check endpoint
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      headers: getHeaders(),
    });
    return response.ok;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
}

/**
 * Price history data point from Polymarket API
 */
export interface PriceHistoryPoint {
  t: number; // Unix timestamp
  p: number; // Price
}

/**
 * Price history response from Polymarket API
 */
export interface PriceHistoryResponse {
  history: PriceHistoryPoint[];
}

/**
 * Fetch price history for a Polymarket market
 */
export async function fetchPriceHistory(clobTokenId: string, interval: string = 'max'): Promise<PriceHistoryResponse> {
  try {
    const response = await fetch(
      `https://clob.polymarket.com/prices-history?market=${encodeURIComponent(clobTokenId)}&interval=${interval}`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to fetch price history: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching price history:', error);
    throw error;
  }
}

