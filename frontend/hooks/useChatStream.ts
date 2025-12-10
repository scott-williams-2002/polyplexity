"use client"

import * as React from "react"
import { streamChat } from "@/lib/api"
import { SSEEvent, ExecutionTraceEvent, Source } from "@/lib/types"

export function useChatStream({ threadId, onThreadIdChange, onMessageSent }: {
  threadId: string | null;
  onThreadIdChange: (threadId: string | null) => void;
  onMessageSent: () => void;
}) {
  const [isStreaming, setIsStreaming] = React.useState(false)
  const [streamingContent, setStreamingContent] = React.useState("")
  const [executionTrace, setExecutionTrace] = React.useState<ExecutionTraceEvent[]>([])
  const [currentStatus, setCurrentStatus] = React.useState<string | null>(null)
  const [sources, setSources] = React.useState<Source[]>([])

  const handleEvent = (event: SSEEvent) => {
    console.log("SSE Event in Hook:", event)

    if (event.event === "thread_id" && event.thread_id) {
      onThreadIdChange(event.thread_id)
    }

    if (event.event === "thread_name") {
      onMessageSent()
    }

    if (event.event === "supervisor_decision") {
      if (event.decision === "research" && event.topic) {
        setCurrentStatus(`Researching: ${event.topic}`)
      } else if (event.decision === "finish") {
        setCurrentStatus("Finalizing response...")
      }
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "supervisor",
        timestamp: Date.now(),
        data: {
          event: "supervisor_decision",
          decision: event.decision,
          reasoning: event.reasoning,
          topic: event.topic || ""
        }
      }
      setExecutionTrace((prev) => [...prev, traceEvent])
    }

    if (event.event === "generated_queries" && event.queries) {
      setCurrentStatus(`Generated ${event.queries.length} search queries...`)
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "generate_queries",
        timestamp: Date.now(),
        data: {
          event: "generated_queries",
          queries: event.queries
        }
      }
      setExecutionTrace((prev) => [...prev, traceEvent])
    }

    if (event.event === "search_start" && event.query) {
      setCurrentStatus(`Searching: ${event.query}`)
      const traceEvent: ExecutionTraceEvent = {
        type: "search",
        node: "perform_search",
        timestamp: Date.now(),
        data: {
          event: "search_start",
          query: event.query
        }
      }
      setExecutionTrace((prev) => [...prev, traceEvent])
    }
    
    if (event.event === "web_search_url" && event.url && event.markdown) {
      setSources((prev) => [...prev, { url: event.url!, markdown: event.markdown! }])
      const match = event.markdown.match(/^\[(.*?)\]/);
      const display = match ? match[1] : event.url;
      setCurrentStatus(`Found source: ${display}`)
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "perform_search",
        timestamp: Date.now(),
        data: {
          event: "web_search_url",
          url: event.url,
          markdown: event.markdown
        }
      }
      setExecutionTrace((prev) => [...prev, traceEvent])
    }

    if (event.event === "research_synthesis_done") {
      setCurrentStatus("Synthesizing research results...")
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "synthesize_research",
        timestamp: Date.now(),
        data: {
          event: "research_synthesis_done"
        }
      }
      setExecutionTrace((prev) => [...prev, traceEvent])
    }

    if (event.event === "writing_report") {
      setCurrentStatus("Writing final report...")
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "final_report",
        timestamp: Date.now(),
        data: {
          event: "writing_report"
        }
      }
      setExecutionTrace((prev) => [...prev, traceEvent])
    }

    if (event.event === "trace" && event.type && event.node) {
      const traceEvent: ExecutionTraceEvent = {
        type: event.type as ExecutionTraceEvent["type"],
        node: event.node,
        timestamp: event.timestamp || Date.now(),
        data: event.data || {},
      }
      setExecutionTrace((prev) => [...prev, traceEvent])
    }

    if (event.type === "update" && event.node && event.data) {
      if (event.node === "final_report" && event.data.final_report) {
        setCurrentStatus(null) // Hide status when content starts streaming
        setStreamingContent(event.data.final_report)
      }
      if (event.node === "supervisor") {
        setCurrentStatus("Analyzing research needs...")
      }
      if (event.node === "call_researcher") {
        setCurrentStatus("Conducting research...")
      }
    }

    if (event.event === "final_report_complete" && event.report) {
      setCurrentStatus(null)
      setStreamingContent(event.report)
      const traceEvent: ExecutionTraceEvent = {
        type: "custom",
        node: "final_report",
        timestamp: Date.now(),
        data: {
          event: "final_report_complete",
          report: event.report
        }
      }
      setExecutionTrace((prev) => [...prev, traceEvent])
    }

    if (event.type === "complete") {
      const finalContent = event.response || streamingContent || ""
      setCurrentStatus(null)
      setStreamingContent(finalContent)
    }

    if (event.event === "thinking" && event.thought) {
      // Note: This is handled in ChatInterface for now, but could be moved here
    }

    if (event.event === "tool_call") {
      // Note: This is handled in ChatInterface for now, but could be moved here
    }

    if (event.event === "error" || event.error) {
      setCurrentStatus("An error occurred.")
    }
  }

  const startStreaming = async (message: string, currentThreadId: string | null) => {
    setIsStreaming(true)
    setStreamingContent("")
    setExecutionTrace([])
    setCurrentStatus("Analyzing request...")
    setSources([])

    try {
      await streamChat(message, currentThreadId, handleEvent)
    } catch (error) {
      console.error("Error streaming chat:", error)
      setCurrentStatus("An error occurred.")
    } finally {
      setIsStreaming(false)
      onMessageSent()
    }
  }

  return {
    isStreaming,
    streamingContent,
    executionTrace,
    currentStatus,
    sources,
    startStreaming,
    // Add reset function for when sending a new message
    reset: () => {
        setIsStreaming(false)
        setStreamingContent("")
        setExecutionTrace([])
        setCurrentStatus(null)
        setSources([])
    }
  }
}
