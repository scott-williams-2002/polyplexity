"use client"

import * as React from "react"
import { ChevronsUpDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { ExecutionTraceEvent } from "@/lib/api"

export interface ExecutionTraceProps {
  events: ExecutionTraceEvent[]
  isStreaming?: boolean
}

export function ExecutionTrace({
  events,
  isStreaming = false,
}: ExecutionTraceProps) {
  const [isOpen, setIsOpen] = React.useState(isStreaming)
  const traceEndRef = React.useRef<HTMLDivElement>(null)

  // Auto-collapse when streaming completes
  React.useEffect(() => {
    if (!isStreaming && events.length > 0) {
      setIsOpen(false)
    }
  }, [isStreaming, events.length])

  // Auto-scroll to bottom during streaming when new events are added
  React.useEffect(() => {
    if (isStreaming && isOpen && events.length > 0) {
      traceEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [events.length, isStreaming, isOpen])

  if (events.length === 0) {
    return null
  }

  // Group events by node for visual organization
  const groupedEvents: { [node: string]: ExecutionTraceEvent[] } = {}
  const chronologicalEvents: ExecutionTraceEvent[] = []

  events.forEach((event) => {
    if (!groupedEvents[event.node]) {
      groupedEvents[event.node] = []
    }
    groupedEvents[event.node].push(event)
    chronologicalEvents.push(event)
  })

  // Sort chronological events by timestamp
  chronologicalEvents.sort((a, b) => a.timestamp - b.timestamp)

  const renderEvent = (event: ExecutionTraceEvent, index: number) => {
    switch (event.type) {
      case "node_call":
        return (
          <div key={index} className="font-bold text-sm py-1">
            → {event.node}
          </div>
        )

      case "reasoning":
        return (
          <div key={index} className="text-sm py-2 pl-4 border-l-2 border-muted">
            <div className="text-xs font-semibold text-muted-foreground mb-1">
              Reasoning:
            </div>
            <div className="text-sm whitespace-pre-wrap">
              {event.data.reasoning || ""}
            </div>
          </div>
        )

      case "search":
        if (event.data.event === "search_start") {
          return (
            <div key={index} className="text-sm py-1 pl-4">
              <span className="text-muted-foreground">Searching:</span>{" "}
              {event.data.query}
            </div>
          )
        } else if (event.data.results) {
          return (
            <div key={index} className="text-sm py-2 pl-4">
              <div className="text-xs font-semibold text-muted-foreground mb-1">
                Found {event.data.results.length} result(s):
              </div>
              <ul className="list-disc list-inside space-y-1">
                {event.data.results.map((result, idx) => (
                  <li key={idx}>
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline hover:text-primary/80"
                    >
                      {result.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )
        }
        return null

      case "state_update":
        return (
          <div key={index} className="text-xs text-muted-foreground py-1 pl-4">
            {event.data.update === "research_notes_added" && (
              <>Research notes added ({event.data.count} total)</>
            )}
            {event.data.update === "iterations_incremented" && (
              <>Iteration {event.data.value}</>
            )}
          </div>
        )

      case "custom":
        if (event.data.event === "supervisor_decision") {
          return (
            <div key={index} className="text-sm py-2 pl-4">
              <div className="text-xs font-semibold text-muted-foreground mb-1">
                Decision: {event.data.decision}
                {event.data.topic && (
                  <>
                    {" "}
                    <span className="text-muted-foreground">Topic:</span>{" "}
                    {event.data.topic}
                  </>
                )}
              </div>
              {event.data.reasoning && (
                <div className="text-sm whitespace-pre-wrap text-muted-foreground mt-1">
                  {event.data.reasoning}
                </div>
              )}
            </div>
          )
        } else if (event.data.event === "generated_queries") {
          return (
            <div key={index} className="text-sm py-2 pl-4">
              <div className="text-xs font-semibold text-muted-foreground mb-1">
                Generated {event.data.queries?.length || 0} search queries:
              </div>
              <ul className="list-disc list-inside space-y-1">
                {event.data.queries?.map((query, idx) => (
                  <li key={idx}>{query}</li>
                ))}
              </ul>
            </div>
          )
        } else if (event.data.event === "research_synthesis_done") {
          return (
            <div key={index} className="text-sm py-1 pl-4 text-muted-foreground">
              Research synthesis complete
            </div>
          )
        } else if (event.data.event === "writing_report") {
          return (
            <div key={index} className="text-sm py-1 pl-4 text-muted-foreground">
              Writing final report...
            </div>
          )
        } else if (event.data.event === "web_search_url") {
          return (
            <div key={index} className="text-sm py-1 pl-4">
              <span className="text-xs text-muted-foreground mr-2">Found:</span>
              <span className="markdown-content inline-block align-middle">
                <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                        p: ({ children }) => <span className="text-sm">{children}</span>,
                        a: ({ href, children }) => (
                            <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary/80">
                                {children}
                            </a>
                        )
                    }}
                >
                    {event.data.markdown || event.data.url}
                </ReactMarkdown>
              </span>
            </div>
          )
        }
        return null

      default:
        return null
    }
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-2">
      <div className="flex items-center justify-between">
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="text-xs">
            <ChevronsUpDown className="size-3 mr-1" />
            {isOpen ? "Hide" : "Show"} execution trace
            {events.length > 0 && (
              <span className="ml-2 text-muted-foreground">
                ({events.length} events)
              </span>
            )}
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className="mt-2">
        <div className="rounded-md border bg-muted/30 p-3 space-y-2 max-h-96 overflow-y-auto">
          {chronologicalEvents.map((event, index) => renderEvent(event, index))}
          {isStreaming && (
            <div className="text-xs text-muted-foreground italic">
              Streaming...
            </div>
          )}
          <div ref={traceEndRef} />
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

