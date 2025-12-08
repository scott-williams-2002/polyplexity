"use client"

import * as React from "react"
import { Send } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Item, ItemContent, ItemMedia, ItemTitle } from "@/components/ui/item"
import { ChatMessage, ChatMessageProps } from "./ChatMessage"
import { streamChat, SSEEvent, getThreadHistory, ExecutionTraceEvent } from "@/lib/api"

interface Message extends ChatMessageProps {
  id: string
  timestamp: Date
}

interface ChatInterfaceProps {
  threadId: string | null
  onThreadIdChange: (threadId: string | null) => void
  onMessageSent: () => void
}

export function ChatInterface({
  threadId,
  onThreadIdChange,
  onMessageSent,
}: ChatInterfaceProps) {
  const [messages, setMessages] = React.useState<Message[]>([])
  const [input, setInput] = React.useState("")
  const [isStreaming, setIsStreaming] = React.useState(false)
  const [currentThoughts, setCurrentThoughts] = React.useState<string[]>([])
  const [currentToolCalls, setCurrentToolCalls] = React.useState<
    Array<{ tool: string; input: any }>
  >([])
  const [streamingContent, setStreamingContent] = React.useState("")
  const [loadingHistory, setLoadingHistory] = React.useState(false)
  const [progressMessage, setProgressMessage] = React.useState<string | null>(null)
  const [executionTrace, setExecutionTrace] = React.useState<ExecutionTraceEvent[]>([])
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)
  const loadedThreadIdRef = React.useRef<string | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  React.useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent])

  // Load thread history when threadId changes
  React.useEffect(() => {
    if (!threadId) {
      // Clear messages and loaded ref when threadId becomes null
      setMessages([])
      loadedThreadIdRef.current = null
      return
    }

    // If threadId changed to a different thread, clear messages and load new history
    if (threadId !== loadedThreadIdRef.current) {
      // Clear messages immediately
      setMessages([])
      loadedThreadIdRef.current = null
      
      // Load history for the new thread
      const loadHistory = async () => {
        try {
          setLoadingHistory(true)
          const history = await getThreadHistory(threadId)
          
          // Convert history messages to Message format
          const formattedMessages: Message[] = history.map((msg, index) => ({
            id: `history-${threadId}-${index}`,
            role: msg.role as "user" | "assistant",
            content: msg.content,
            timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
            execution_trace: msg.execution_trace,
          }))
          
          // Use functional update to ensure we replace, not append
          // This replaces whatever is in messages, regardless of current state
          setMessages(() => formattedMessages)
          loadedThreadIdRef.current = threadId
        } catch (error) {
          console.error("Failed to load thread history:", error)
          // If thread not found or error, clear loaded ref so we can try again
          loadedThreadIdRef.current = null
        } finally {
          setLoadingHistory(false)
        }
      }
      
      // Load immediately - setMessages([]) will clear, then we load
      loadHistory()
    }
  }, [threadId])

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsStreaming(true)
    setCurrentThoughts([])
    setCurrentToolCalls([])
    setStreamingContent("")
    setProgressMessage("Researching and generating response...")
    setExecutionTrace([]) // Reset trace for new message

    let currentThreadId = threadId
    let assistantMessageId = `assistant-${Date.now()}`
    
    // Add placeholder assistant message immediately with execution_trace
    const placeholderMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isStreaming: true,
      execution_trace: [], // Initialize empty, will be updated as events come in
    }
    setMessages((prev) => [...prev, placeholderMessage])

    try {
      await streamChat(
        userMessage.content,
        currentThreadId,
        (event: SSEEvent) => {
          // Log all incoming SSE events for debugging
          console.log("SSE Event:", event)
          
          // Handle thread_id event
          if (event.event === "thread_id" && event.thread_id) {
            currentThreadId = event.thread_id
            onThreadIdChange(event.thread_id)
          }

          // Handle thread_name event - trigger sidebar refresh when name is received
          if (event.event === "thread_name" && event.name) {
            // Trigger sidebar refresh by calling onMessageSent
            // This will cause the sidebar to reload and show the new thread name
            onMessageSent()
          }

          // Handle research agent events and add them to execution trace
          if (event.event === "supervisor_decision") {
            if (event.decision === "research" && event.topic) {
              setProgressMessage(`Researching: ${event.topic}`)
            } else if (event.decision === "finish") {
              setProgressMessage("Writing final report...")
            }
            // Add to execution trace
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
            setProgressMessage(`Generated ${event.queries.length} search queries...`)
            // Add to execution trace
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
            setProgressMessage(`Searching: ${event.query}`)
            // Add to execution trace
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

          if (event.event === "research_synthesis_done") {
            setProgressMessage("Synthesizing research results...")
            // Add to execution trace
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
            setProgressMessage("Writing final report...")
            // Add to execution trace
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

          if (event.event === "final_report_complete" && event.report) {
            setStreamingContent(event.report)
            setProgressMessage(null)
            // Add to execution trace
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

          // Handle thinking events
          if (event.event === "thinking" && event.thought) {
            setCurrentThoughts((prev) => [...prev, event.thought!])
          }

          // Handle tool_call events
          if (event.event === "tool_call") {
            setCurrentToolCalls((prev) => [
              ...prev,
              {
                tool: event.tool || "unknown",
                input: event.input || {},
              },
            ])
          }

          // Handle trace events
          if (event.event === "trace" && event.type && event.node) {
            const traceEvent: ExecutionTraceEvent = {
              type: event.type as ExecutionTraceEvent["type"],
              node: event.node,
              timestamp: event.timestamp || Date.now(),
              data: event.data || {}
            }
            setExecutionTrace((prev) => [...prev, traceEvent])
          }

          // Handle update events (state updates) - incremental updates
          if (event.type === "update" && event.node && event.data) {
            // Incrementally update final_report as it streams in
            if (event.node === "final_report" && event.data.final_report) {
              setStreamingContent(event.data.final_report)
            }
            // Update progress for other nodes
            if (event.node === "supervisor") {
              setProgressMessage("Analyzing research needs...")
            }
            if (event.node === "call_researcher") {
              setProgressMessage("Conducting research...")
            }
          }

          // Handle complete event
          if (event.type === "complete") {
            // Use response from complete event, or fall back to streamingContent
            const finalContent = event.response || streamingContent || ""
            setProgressMessage(null)
            setMessages((prev) => {
              // Filter out any duplicate messages with the same content that might have been added
              const seen = new Set<string>()
              const deduplicated = prev.filter((msg) => {
                const key = `${msg.role}-${msg.content.substring(0, 50)}`
                if (seen.has(key)) {
                  return false
                }
                seen.add(key)
                return true
              })
              
              const updated = [...deduplicated]
              const assistantIndex = updated.findIndex(
                (m) => m.id === assistantMessageId
              )
              const assistantMessage: Message = {
                id: assistantMessageId,
                role: "assistant",
                content: finalContent,
                thoughts: currentThoughts.length > 0 ? [...currentThoughts] : undefined,
                toolCalls:
                  currentToolCalls.length > 0 ? [...currentToolCalls] : undefined,
                timestamp: new Date(),
                isStreaming: false,
                execution_trace: executionTrace.length > 0 ? [...executionTrace] : undefined,
              }

              if (assistantIndex >= 0) {
                updated[assistantIndex] = assistantMessage
              } else {
                // Check if this message already exists before adding
                const exists = updated.some(
                  (m) => m.role === assistantMessage.role && m.content === assistantMessage.content
                )
                if (!exists) {
                  updated.push(assistantMessage)
                }
              }
              return updated
            })
            setIsStreaming(false)
            setStreamingContent("")
            setCurrentThoughts([])
            setCurrentToolCalls([])
            setProgressMessage(null)
            setExecutionTrace([])
            onMessageSent()
          }

          // Handle error events
          if (event.event === "error" || event.error) {
            const errorMessage: Message = {
              id: `error-${Date.now()}`,
              role: "assistant",
              content: `Error: ${event.error || "Unknown error occurred"}`,
              timestamp: new Date(),
            }
            setMessages((prev) => [...prev, errorMessage])
            setIsStreaming(false)
            setStreamingContent("")
            setCurrentThoughts([])
            setCurrentToolCalls([])
            setProgressMessage(null)
            setExecutionTrace([])
          }
        }
      )

      // Ensure message is finalized if streaming ended without complete event
      if (isStreaming && streamingContent) {
        setMessages((prev) => {
          const updated = [...prev]
          const assistantIndex = updated.findIndex((m) => m.id === assistantMessageId)
          if (assistantIndex >= 0) {
            updated[assistantIndex] = {
              ...updated[assistantIndex],
              content: streamingContent,
              thoughts: currentThoughts.length > 0 ? [...currentThoughts] : undefined,
              toolCalls: currentToolCalls.length > 0 ? [...currentToolCalls] : undefined,
              isStreaming: false,
            }
          }
          return updated
        })
        setIsStreaming(false)
        setStreamingContent("")
        setCurrentThoughts([])
        setCurrentToolCalls([])
        setProgressMessage(null)
        setExecutionTrace([])
        onMessageSent()
      }
    } catch (error) {
      console.error("Error streaming chat:", error)
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Failed to send message"}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
      setIsStreaming(false)
      setStreamingContent("")
      setCurrentThoughts([])
      setCurrentToolCalls([])
      setProgressMessage(null)
      setExecutionTrace([])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Update assistant message while streaming (incremental updates)
  // This includes updating execution trace even when content is empty
  React.useEffect(() => {
    if (isStreaming) {
      setMessages((prev) => {
        const updated = [...prev]
        // Find the last assistant message that's streaming
        let foundStreaming = false
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === "assistant" && updated[i].isStreaming) {
            updated[i] = {
              ...updated[i],
              content: streamingContent || "",
              thoughts: currentThoughts.length > 0 ? [...currentThoughts] : undefined,
              toolCalls:
                currentToolCalls.length > 0 ? [...currentToolCalls] : undefined,
              execution_trace: [...executionTrace], // Always set, even if empty, so updates are visible
              isStreaming: true,
            }
            foundStreaming = true
            break
          }
        }
        // If no streaming message found, add a new one (even if content is empty, to show trace)
        if (!foundStreaming) {
          updated.push({
            id: `assistant-streaming-${Date.now()}`,
            role: "assistant",
            content: streamingContent || "",
            thoughts: currentThoughts.length > 0 ? [...currentThoughts] : undefined,
            toolCalls:
              currentToolCalls.length > 0 ? [...currentToolCalls] : undefined,
            timestamp: new Date(),
            isStreaming: true,
            execution_trace: [...executionTrace], // Always set, even if empty, so updates are visible
          })
        }
        return updated
      })
    }
  }, [streamingContent, isStreaming, currentThoughts, currentToolCalls, executionTrace])

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loadingHistory && (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center">
              <Spinner className="mx-auto mb-2" />
              <p className="text-sm">Loading conversation history...</p>
            </div>
          </div>
        )}
        {messages.length === 0 && !isStreaming && !loadingHistory && (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center">
              <p className="text-lg font-medium mb-2">Start a conversation</p>
              <p className="text-sm">Type a message below to begin chatting.</p>
            </div>
          </div>
        )}
        {messages.map((message) => (
          <ChatMessage key={message.id} {...message} />
        ))}
        {isStreaming && progressMessage && (
          <Item variant="muted" className="max-w-xs">
            <ItemMedia>
              <Spinner />
            </ItemMedia>
            <ItemContent>
              <ItemTitle className="line-clamp-1">{progressMessage}</ItemTitle>
            </ItemContent>
          </Item>
        )}
        {isStreaming && !progressMessage && (
          <Item variant="muted" className="max-w-xs">
            <ItemMedia>
              <Spinner />
            </ItemMedia>
            <ItemContent>
              <ItemTitle className="line-clamp-1">Researching and generating response...</ItemTitle>
            </ItemContent>
          </Item>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t p-4">
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message here..."
              rows={3}
              disabled={isStreaming}
              className="resize-none"
            />
          </div>
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="h-10 w-10"
          >
            <Send className="size-4" />
            <span className="sr-only">Send message</span>
          </Button>
        </div>
      </div>
    </div>
  )
}

