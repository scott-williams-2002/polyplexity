"use client"

import * as React from "react"
import { Send } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Item, ItemContent, ItemMedia, ItemTitle } from "@/components/ui/item"
import { ChatMessage, ChatMessageProps } from "./ChatMessage"
import { getThreadHistory } from "@/lib/api"
import { Message as ApiMessage } from "@/lib/types"
import { useChatStream } from "@/hooks/useChatStream"

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
  const [loadingHistory, setLoadingHistory] = React.useState(false)
  const [currentThoughts, setCurrentThoughts] = React.useState<string[]>([])
  const [currentToolCalls, setCurrentToolCalls] = React.useState<
    Array<{ tool: string; input: any }>
  >([])
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)
  const loadedThreadIdRef = React.useRef<string | null>(null)
  
  const {
    isStreaming,
    streamingContent,
    executionTrace,
    currentStatus,
    sources,
    startStreaming,
    reset: resetStream,
  } = useChatStream({
    threadId,
    onThreadIdChange,
    onMessageSent,
  })

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
    setCurrentThoughts([])
    setCurrentToolCalls([])
    resetStream()

    let assistantMessageId = `assistant-${Date.now()}`
    
    // Add placeholder assistant message immediately
    const placeholderMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isStreaming: true,
      execution_trace: [],
      currentStatus: null,
      sources: [],
    }
    setMessages((prev) => [...prev, placeholderMessage])

    try {
      await startStreaming(userMessage.content, threadId)
      
      // Finalize the message after streaming completes
      setMessages((prev) => {
        const updated = [...prev]
        const assistantIndex = updated.findIndex((m) => m.id === assistantMessageId)
        if (assistantIndex >= 0) {
          updated[assistantIndex] = {
            ...updated[assistantIndex],
            content: streamingContent || "",
            thoughts: currentThoughts.length > 0 ? [...currentThoughts] : undefined,
            toolCalls: currentToolCalls.length > 0 ? [...currentToolCalls] : undefined,
            isStreaming: false,
            execution_trace: executionTrace.length > 0 ? [...executionTrace] : undefined,
            sources: sources.length > 0 ? [...sources] : undefined,
          }
        }
        return updated
      })
    } catch (error) {
      console.error("Error streaming chat:", error)
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Failed to send message"}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
      resetStream()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Update assistant message while streaming (incremental updates)
  // This includes updating execution trace, status, and sources even when content is empty
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
              currentStatus: currentStatus,
              sources: [...sources],
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
            currentStatus: currentStatus,
            sources: [...sources],
          })
        }
        return updated
      })
    } else if (!isStreaming && streamingContent) {
      // Finalize message when streaming completes
      setMessages((prev) => {
        const updated = [...prev]
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === "assistant" && updated[i].isStreaming) {
            updated[i] = {
              ...updated[i],
              content: streamingContent,
              thoughts: currentThoughts.length > 0 ? [...currentThoughts] : undefined,
              toolCalls: currentToolCalls.length > 0 ? [...currentToolCalls] : undefined,
              execution_trace: executionTrace.length > 0 ? [...executionTrace] : undefined,
              sources: sources.length > 0 ? [...sources] : undefined,
              isStreaming: false,
              currentStatus: null,
            }
            break
          }
        }
        return updated
      })
    }
  }, [streamingContent, isStreaming, currentThoughts, currentToolCalls, executionTrace, currentStatus, sources])

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

