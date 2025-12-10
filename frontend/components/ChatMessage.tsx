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
import { ExecutionTrace } from "./ExecutionTrace"
import { StatusIndicator } from "./StatusIndicator"
import { Sources } from "./Sources"

import { ExecutionTraceEvent, Source } from "@/lib/types"

export interface ChatMessageProps {
  role: "user" | "assistant"
  content: string
  thoughts?: string[]
  toolCalls?: Array<{ tool: string; input: any }>
  isStreaming?: boolean
  execution_trace?: ExecutionTraceEvent[]
  currentStatus?: string | null
  sources?: Source[]
}

export function ChatMessage({ 
  role, 
  content, 
  thoughts = [], 
  toolCalls = [],
  isStreaming = false,
  execution_trace = [],
  currentStatus = null,
  sources = []
}: ChatMessageProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const hasThoughts = thoughts.length > 0 || toolCalls.length > 0

  return (
    <div className={`flex flex-col gap-2 p-4 rounded-lg ${
      role === "user" 
        ? "bg-muted ml-auto max-w-[80%]" 
        : "bg-background border mr-auto max-w-[80%]"
    }`}>
      {/* Execution Trace - shown first, collapsed by default when not streaming */}
      {/* Show trace even when content is empty during streaming */}
      {execution_trace && execution_trace.length > 0 && role === "assistant" && (
        <ExecutionTrace
          events={execution_trace}
          isStreaming={isStreaming}
        />
      )}
      
      {/* Status indicator - shown when streaming and content is empty */}
      {isStreaming && !content && currentStatus && role === "assistant" && (
        <StatusIndicator status={currentStatus} />
      )}
      
      {/* Content area - shown when there's content or it's not streaming */}
      {(content || !isStreaming) && (
        <>
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="text-sm font-semibold mb-1">
                {role === "user" ? "You" : "Assistant"}
              </div>
              {content && (
                <div className="text-sm markdown-content max-w-full overflow-hidden">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      // Customize markdown components for better styling
                      p: ({ children }) => <p className="mb-2 last:mb-0 break-words">{children}</p>,
                      h1: ({ children }) => <h1 className="text-xl font-bold mb-2 mt-4 first:mt-0 break-words">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-lg font-semibold mb-2 mt-3 first:mt-0 break-words">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-base font-semibold mb-1 mt-2 first:mt-0 break-words">{children}</h3>,
                      ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1 break-words">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1 break-words">{children}</ol>,
                      li: ({ children }) => <li className="ml-2 break-words">{children}</li>,
                      code: ({ children, className }) => {
                        const isInline = !className
                        return isInline ? (
                          <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono break-words">{children}</code>
                        ) : (
                          <code className={className}>{children}</code>
                        )
                      },
                      pre: ({ children }) => (
                        <pre className="bg-muted p-3 rounded-md overflow-x-auto mb-2 text-xs font-mono max-w-full">
                          {children}
                        </pre>
                      ),
                      a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary/80 break-words">
                          {children}
                        </a>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-4 border-muted-foreground/30 pl-4 italic my-2 break-words">
                          {children}
                        </blockquote>
                      ),
                      table: ({ children }) => (
                        <div className="overflow-x-auto my-2 max-w-full">
                          <table className="w-full border-collapse border border-border table-auto">
                            {children}
                          </table>
                        </div>
                      ),
                      thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
                      th: ({ children }) => (
                        <th className="border border-border px-3 py-2 text-left font-semibold break-words">
                          {children}
                        </th>
                      ),
                      td: ({ children }) => (
                        <td className="border border-border px-3 py-2 break-words">
                          {children}
                        </td>
                      ),
                      hr: () => <hr className="my-4 border-border" />,
                      strong: ({ children }) => <strong className="font-semibold break-words">{children}</strong>,
                      em: ({ children }) => <em className="italic break-words">{children}</em>,
                    }}
                  >
                    {content}
                  </ReactMarkdown>
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1 align-middle" />
                  )}
                </div>
              )}
            </div>
            {hasThoughts && (
              <Collapsible open={isOpen} onOpenChange={setIsOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="icon" className="size-6 shrink-0">
                    <ChevronsUpDown className="size-4" />
                    <span className="sr-only">Toggle reasoning</span>
                  </Button>
                </CollapsibleTrigger>
              </Collapsible>
            )}
          </div>
          
          {hasThoughts && (
            <Collapsible open={isOpen} onOpenChange={setIsOpen}>
              <CollapsibleContent className="flex flex-col gap-2 mt-2 pt-2 border-t">
                {thoughts.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-muted-foreground">
                      Reasoning:
                    </div>
                    {thoughts.map((thought, index) => (
                      <div 
                        key={index}
                        className="rounded-md border px-3 py-2 font-mono text-xs bg-muted/50"
                      >
                        {thought}
                      </div>
                    ))}
                  </div>
                )}
                {toolCalls.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-muted-foreground">
                      Tool Calls:
                    </div>
                    {toolCalls.map((toolCall, index) => (
                      <div 
                        key={index}
                        className="rounded-md border px-3 py-2 font-mono text-xs bg-muted/50"
                      >
                        <div className="font-semibold">{toolCall.tool}</div>
                        <div className="text-muted-foreground mt-1">
                          {JSON.stringify(toolCall.input, null, 2)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CollapsibleContent>
            </Collapsible>
          )}
          
          {/* Sources - shown at the bottom for assistant messages */}
          {role === "assistant" && sources && sources.length > 0 && (
            <Sources sources={sources} />
          )}
        </>
      )}
    </div>
  )
}

