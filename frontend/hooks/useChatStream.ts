import { useState, useCallback, useEffect, useRef } from "react";
import { streamChat } from "../lib/api";
import { SSEEvent, ExecutionTraceEvent, Source, StreamStage, ApprovedMarket } from "../types";
import { executionTraceToReasoning } from "../lib/adapters";

interface UseChatStreamProps {
  threadId: string | null;
  onThreadIdChange: (threadId: string | null) => void;
  onMessageSent: () => void;
}

/**
 * Normalize an event to ExecutionTraceEvent format.
 * Handles both envelope format (from streaming) and direct format (from refresh).
 */
function normalizeToExecutionTraceEvent(event: SSEEvent | ExecutionTraceEvent): ExecutionTraceEvent | null {
  // Check if it's already in ExecutionTraceEvent format (from refresh)
  // Direct format has: type, node, timestamp, data (no payload)
  if (
    'type' in event && 
    'node' in event && 
    'timestamp' in event && 
    'data' in event && 
    !('payload' in event) &&
    typeof (event as any).type === 'string' &&
    ['node_call', 'reasoning', 'search', 'state_update', 'custom'].includes((event as any).type)
  ) {
    return event as ExecutionTraceEvent;
  }

  // Check if it's envelope format (from streaming)
  // Envelope format has: type, node, event, payload, timestamp
  // Type guard: ExecutionTraceEvent doesn't have 'event' or 'payload' properties
  if ('event' in event && 'payload' in event && event.type && event.node) {
    const envelopeEvent = event as SSEEvent & { type: string; node: string; event: string; payload: any; timestamp?: number };
    
    // Extract trace type from envelope
    let traceType: ExecutionTraceEvent["type"] = "custom";
    let eventData: any = {};
    let eventTimestamp: number = envelopeEvent.timestamp || Date.now();
    
    if (envelopeEvent.type === "trace") {
      // For trace events, the payload contains the trace event itself: {type, node, timestamp, data}
      if (envelopeEvent.payload?.type) {
        traceType = envelopeEvent.payload.type as ExecutionTraceEvent["type"];
        // Extract data from nested trace event
        eventData = envelopeEvent.payload.data || {};
        eventTimestamp = envelopeEvent.payload.timestamp || envelopeEvent.timestamp || Date.now();
      } else {
        // Fallback: use event name to determine type
        const eventName = envelopeEvent.event;
        if (eventName === "node_call") traceType = "node_call";
        else if (eventName === "reasoning") traceType = "reasoning";
        else if (eventName === "search") traceType = "search";
        else if (eventName === "state_update") traceType = "state_update";
        else traceType = "custom";
        eventData = envelopeEvent.payload || {};
      }
      // Include the event name in data
      eventData.event = envelopeEvent.event;
    } else if (envelopeEvent.type === "custom") {
      traceType = "custom";
      // Custom events: payload contains event data directly
      eventData = { ...envelopeEvent.payload };
      eventData.event = envelopeEvent.event;
    } else if (envelopeEvent.type === "state_update") {
      traceType = "state_update";
      // State update events: payload contains update data directly
      eventData = { ...envelopeEvent.payload };
      eventData.event = envelopeEvent.event;
    } else {
      // Unknown type, skip normalization
      return null;
    }

    return {
      type: traceType,
      node: envelopeEvent.node,
      timestamp: eventTimestamp,
      data: eventData,
    };
  }

  return null;
}

export function useChatStream({
  threadId,
  onThreadIdChange,
  onMessageSent,
}: UseChatStreamProps) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [executionTrace, setExecutionTrace] = useState<ExecutionTraceEvent[]>([]);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [stage, setStage] = useState<StreamStage>("idle");
  const [finalReportComplete, setFinalReportComplete] = useState(false);
  const [approvedMarkets, setApprovedMarkets] = useState<ApprovedMarket[]>([]);
  const [polymarketBlurb, setPolymarketBlurb] = useState<string | null>(null);
  const approvedMarketsRef = useRef<ApprovedMarket[]>([]);
  const polymarketBlurbRef = useRef<string | null>(null);

  const handleEvent = useCallback((event: SSEEvent) => {
    console.log('[useChatStream] Handling event:', event);
    
    // Check if this is envelope format (new standardized format)
    const isEnvelopeFormat = event.type && event.event !== undefined && event.payload !== undefined;
    
    // Extract data from envelope format or use legacy format
    const getPayload = () => {
      if (isEnvelopeFormat) {
        return event.payload || {};
      }
      // Legacy format - return event itself as payload
      return event;
    };
    
    const payload = getPayload();
    const eventName = isEnvelopeFormat ? event.event : (event.event || '');
    const eventType = isEnvelopeFormat ? event.type : (event.type || '');
    const eventNode = isEnvelopeFormat ? event.node : (event.node || '');

    // Handle system events
    if (eventType === "system" || eventName === "thread_id") {
      const threadId = payload.thread_id || event.thread_id;
      if (threadId) {
        onThreadIdChange(threadId);
      }
    }

    if (eventName === "thread_name") {
      onMessageSent();
    }

    // Normalize event to ExecutionTraceEvent and add to trace
    const normalizedEvent = normalizeToExecutionTraceEvent(event);
    if (normalizedEvent) {
      setExecutionTrace((prev) => [...prev, normalizedEvent]);
    } else if (!isEnvelopeFormat && event.event) {
      // Legacy format: try to create ExecutionTraceEvent from flat structure
      // This handles old events that don't have envelope format
      const legacyEvent: ExecutionTraceEvent = {
        type: (event.type as ExecutionTraceEvent["type"]) || "custom",
        node: event.node || "unknown",
        timestamp: event.timestamp || Date.now(),
        data: {
          event: event.event,
          ...(event.data || {}),
          // Include legacy flat properties
          decision: event.decision,
          reasoning: event.reasoning,
          topic: event.topic,
          queries: event.queries,
          query: event.query,
          report: event.report,
          url: event.url,
          markdown: event.markdown,
        },
      };
      setExecutionTrace((prev) => [...prev, legacyEvent]);
    }

    // Handle specific event types for UI state updates
    if (eventName === "supervisor_decision") {
      const decision = payload.decision || event.decision;
      const topic = payload.topic || event.topic;
      const reasoning = payload.reasoning || event.reasoning;
      
      if (decision === "research" && topic) {
        setCurrentStatus(`Researching: ${topic}`);
        setStage("searching");
      } else if (decision === "finish") {
        setCurrentStatus("Finalizing response...");
        setStage("answering");
      }
    }

    if (eventName === "generated_queries") {
      const queries = payload.queries || event.queries;
      if (queries) {
        setCurrentStatus(`Generated ${queries.length} search queries...`);
        setStage("searching");
      }
    }

    if (eventName === "search_start") {
      const query = payload.query || event.query;
      if (query) {
        setCurrentStatus(`Searching: ${query}`);
        setStage("searching");
      }
    }

    if (eventName === "web_search_url") {
      const url = payload.url || event.url;
      const markdown = payload.markdown || event.markdown;
      if (url && markdown) {
        setSources((prev) => [...prev, { url, markdown }]);
        const match = markdown.match(/^\[(.*?)\]/);
        const display = match ? match[1] : url;
        setCurrentStatus(`Found source: ${display}`);
        setStage("searching");
      }
    }

    // Extract URLs from trace events with search results (fallback if web_search_url events don't come through)
    if (eventType === "trace" && eventName === "search") {
      // For envelope format trace events, payload contains the trace event: {type, node, timestamp, data}
      // The data field contains the search results
      let searchData: any = {};
      
      if (isEnvelopeFormat) {
        // Envelope format: payload.data contains the results
        if (payload.data && payload.data.results) {
          searchData = payload.data;
        } else if (payload.results) {
          // Fallback: results might be directly in payload
          searchData = { results: payload.results };
        }
      } else {
        // Legacy format: check event.data or event directly
        searchData = event.data || event;
      }
      
      if (searchData.results && Array.isArray(searchData.results)) {
        searchData.results.forEach((result: { title?: string; url?: string }) => {
          if (result.url) {
            // Create markdown format for the URL
            const title = result.title || result.url;
            const markdown = `[${title}](${result.url})`;
            setSources((prev) => {
              // Avoid duplicates
              if (!prev.some(s => s.url === result.url)) {
                return [...prev, { url: result.url, markdown: markdown }];
              }
              return prev;
            });
          }
        });
      }
    }

    if (eventName === "research_synthesis_done") {
      setCurrentStatus("Synthesizing research results...");
      setStage("reasoning");
    }

    if (eventName === "writing_report") {
      setCurrentStatus("Writing final report...");
      setStage("answering");
    }

    if (eventName === "final_report_complete") {
      const report = payload.report || event.report;
      setCurrentStatus(null);
      setStage("completed");
      setFinalReportComplete(true);
      if (report) {
        setStreamingContent((prev) => report || prev);
      }
    }

    // Handle market research events
    if (eventName === "market_research_start") {
      setCurrentStatus("Starting market research...");
      setStage("searching");
    }

    if (eventName === "tag_selected") {
      const tags = payload.tags;
      if (tags && Array.isArray(tags)) {
        setCurrentStatus(`Selected ${tags.length} relevant market tags...`);
        setStage("searching");
      }
    }

    if (eventName === "market_approved") {
      const question = payload.question;
      if (question) {
        setCurrentStatus(`Found market: ${question.substring(0, 60)}...`);
        setStage("searching");
      }
    }

    if (eventName === "market_research_complete") {
      const reasoning = payload.reasoning || event.reasoning;
      setCurrentStatus("Market research complete");
      setStage("answering");
    }

    if (eventName === "polymarket_blurb_generated") {
      setCurrentStatus("Generated market recommendations");
      setStage("answering");
    }

    // Handle state_update events
    if (eventType === "state_update") {
      // Handle approved_markets from call_market_research node
      if (eventNode === "call_market_research" && payload.approved_markets && Array.isArray(payload.approved_markets)) {
        setApprovedMarkets(payload.approved_markets);
        approvedMarketsRef.current = payload.approved_markets;
      }
      // Handle polymarket_blurb from rewrite_polymarket_response node
      if (eventNode === "rewrite_polymarket_response" && payload.polymarket_blurb && typeof payload.polymarket_blurb === "string") {
        setPolymarketBlurb(payload.polymarket_blurb);
        polymarketBlurbRef.current = payload.polymarket_blurb;
      }
      // Handle final_report updates
      if (payload.final_report !== undefined) {
        setCurrentStatus(null);
        setStage("answering");
        setStreamingContent((prev) => payload.final_report || prev);
      }
      // Handle research_notes updates
      if (payload.research_notes !== undefined) {
        setCurrentStatus("Conducting research...");
        setStage("searching");
      }
      // Handle iterations updates
      if (payload.iterations !== undefined) {
        setCurrentStatus("Analyzing research needs...");
        setStage("reasoning");
      }
    }

    // Handle legacy update format (for backward compatibility)
    if (eventType === "update" && eventNode && payload) {
      if (eventNode === "final_report" && payload.final_report) {
        setCurrentStatus(null);
        setStage("answering");
        setStreamingContent((prev) => payload.final_report || prev);
      }
      if (eventNode === "supervisor") {
        setCurrentStatus("Analyzing research needs...");
        setStage("reasoning");
      }
      if (eventNode === "call_researcher") {
        setCurrentStatus("Conducting research...");
        setStage("searching");
      }
    }

    // Handle completion events
    if (eventType === "complete") {
      const finalContent = payload.response || event.response || streamingContent || "";
      setCurrentStatus(null);
      setStage("completed");
      setStreamingContent(finalContent);
    }

    // Handle error events
    if (eventType === "error" || eventName === "error" || event.error) {
      const errorMsg = payload.error || event.error || "An error occurred.";
      setCurrentStatus(errorMsg);
      setStage("completed");
    }
  }, [onThreadIdChange, onMessageSent, streamingContent]);

  const startStreaming = useCallback(async (message: string, currentThreadId: string | null) => {
    // Reset all streaming state
    setIsStreaming(true);
    setStreamingContent("");
    setExecutionTrace([]);
    setCurrentStatus("Analyzing request...");
    setSources([]);
    setStage("searching");
    setFinalReportComplete(false);
    setApprovedMarkets([]);
    setPolymarketBlurb(null);
    approvedMarketsRef.current = [];
    polymarketBlurbRef.current = null;

    try {
      await streamChat(message, currentThreadId, handleEvent);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      console.error("Error streaming chat:", errorMessage);
      setCurrentStatus(errorMessage.includes("Network error") || errorMessage.includes("Unable to connect")
        ? "Connection error: Please check if backend is running"
        : "An error occurred: " + errorMessage);
      setStage("completed");
    } finally {
      // Mark as completed but don't reset immediately - let the UI update first
      setIsStreaming(false);
      setStage("completed");
      onMessageSent();
    }
  }, [handleEvent, onMessageSent]);

  const reset = useCallback(() => {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/5926f707-95e8-4111-b824-adadbab0a6a6',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'useChatStream.ts:373',message:'reset called',data:{approvedMarketsCount:approvedMarketsRef.current.length,hasPolymarketBlurb:!!polymarketBlurbRef.current},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    setIsStreaming(false);
    setStreamingContent("");
    setExecutionTrace([]);
    setCurrentStatus(null);
    setSources([]);
    setStage("idle");
    setFinalReportComplete(false);
    setApprovedMarkets([]);
    setPolymarketBlurb(null);
    approvedMarketsRef.current = [];
    polymarketBlurbRef.current = null;
  }, []);

  // Convert execution trace to reasoning string
  const reasoning = executionTraceToReasoning(executionTrace);
  
  // Debug logging
  useEffect(() => {
    console.log('[useChatStream] executionTrace length:', executionTrace.length);
    console.log('[useChatStream] reasoning:', reasoning);
  }, [executionTrace, reasoning]);

  return {
    isStreaming,
    streamingContent,
    executionTrace,
    reasoning,
    currentStatus,
    sources,
    stage,
    finalReportComplete,
    approvedMarkets,
    polymarketBlurb,
    startStreaming,
    reset,
  };
}

