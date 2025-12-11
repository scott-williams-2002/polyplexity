import { useState, useCallback, useEffect } from "react";
import { streamChat } from "../lib/api";
import { SSEEvent, ExecutionTraceEvent, Source, StreamStage } from "../types";
import { executionTraceToReasoning } from "../lib/adapters";

interface UseChatStreamProps {
  threadId: string | null;
  onThreadIdChange: (threadId: string | null) => void;
  onMessageSent: () => void;
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

  const handleEvent = useCallback((event: SSEEvent) => {
    console.log('[useChatStream] Handling event:', event);
    
    if (event.event === "thread_id" && event.thread_id) {
      onThreadIdChange(event.thread_id);
    }

    if (event.event === "thread_name") {
      onMessageSent();
    }

    if (event.event === "supervisor_decision") {
      if (event.decision === "research" && event.topic) {
        setCurrentStatus(`Researching: ${event.topic}`);
        setStage("searching");
      } else if (event.decision === "finish") {
        setCurrentStatus("Finalizing response...");
        setStage("answering");
      }
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "supervisor",
        timestamp: Date.now(),
        data: {
          event: "supervisor_decision",
          decision: event.decision,
          reasoning: event.reasoning,
          topic: event.topic || "",
        },
      };
      setExecutionTrace((prev) => [...prev, traceEvent]);
    }

    if (event.event === "generated_queries" && event.queries) {
      setCurrentStatus(`Generated ${event.queries.length} search queries...`);
      setStage("searching");
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "generate_queries",
        timestamp: Date.now(),
        data: {
          event: "generated_queries",
          queries: event.queries,
        },
      };
      setExecutionTrace((prev) => [...prev, traceEvent]);
    }

    if (event.event === "search_start" && event.query) {
      setCurrentStatus(`Searching: ${event.query}`);
      setStage("searching");
      const traceEvent: ExecutionTraceEvent = {
        type: "search",
        node: "perform_search",
        timestamp: Date.now(),
        data: {
          event: "search_start",
          query: event.query,
        },
      };
      setExecutionTrace((prev) => [...prev, traceEvent]);
    }

    if (event.event === "web_search_url" && event.url && event.markdown) {
      setSources((prev) => [...prev, { url: event.url!, markdown: event.markdown! }]);
      const match = event.markdown.match(/^\[(.*?)\]/);
      const display = match ? match[1] : event.url;
      setCurrentStatus(`Found source: ${display}`);
      setStage("searching");
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "perform_search",
        timestamp: Date.now(),
        data: {
          event: "web_search_url",
          url: event.url,
          markdown: event.markdown,
        },
      };
      setExecutionTrace((prev) => [...prev, traceEvent]);
    }

    if (event.event === "research_synthesis_done") {
      setCurrentStatus("Synthesizing research results...");
      setStage("reasoning");
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "synthesize_research",
        timestamp: Date.now(),
        data: {
          event: "research_synthesis_done",
        },
      };
      setExecutionTrace((prev) => [...prev, traceEvent]);
    }

    if (event.event === "writing_report") {
      setCurrentStatus("Writing final report...");
      setStage("answering");
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "final_report",
        timestamp: Date.now(),
        data: {
          event: "writing_report",
        },
      };
      setExecutionTrace((prev) => [...prev, traceEvent]);
    }

    if (event.event === "trace" && event.type && event.node) {
      const traceEvent: ExecutionTraceEvent = {
        type: event.type as ExecutionTraceEvent["type"],
        node: event.node,
        timestamp: event.timestamp || Date.now(),
        data: event.data || {},
      };
      setExecutionTrace((prev) => [...prev, traceEvent]);
    }

    if (event.type === "update" && event.node && event.data) {
      if (event.node === "final_report" && event.data.final_report) {
        setCurrentStatus(null);
        setStage("answering");
        // Update streaming content immediately - this will trigger UI update
        setStreamingContent((prev) => {
          // If we're getting incremental updates, append; otherwise replace
          const newContent = event.data.final_report || "";
          return newContent;
        });
      }
      if (event.node === "supervisor") {
        setCurrentStatus("Analyzing research needs...");
        setStage("reasoning");
      }
      if (event.node === "call_researcher") {
        setCurrentStatus("Conducting research...");
        setStage("searching");
      }
    }

    if (event.event === "final_report_complete" && event.report) {
      setCurrentStatus(null);
      setStage("completed");
      setFinalReportComplete(true);
      // Update content immediately
      setStreamingContent((prev) => event.report || prev);
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "final_report",
        timestamp: Date.now(),
        data: {
          event: "final_report_complete",
          report: event.report,
        },
      };
      setExecutionTrace((prev) => [...prev, traceEvent]);
    }

    if (event.type === "complete") {
      const finalContent = event.response || streamingContent || "";
      setCurrentStatus(null);
      setStage("completed");
      setStreamingContent(finalContent);
    }

    if (event.event === "error" || event.error) {
      setCurrentStatus("An error occurred.");
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
    setIsStreaming(false);
    setStreamingContent("");
    setExecutionTrace([]);
    setCurrentStatus(null);
    setSources([]);
    setStage("idle");
    setFinalReportComplete(false);
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
    startStreaming,
    reset,
  };
}

