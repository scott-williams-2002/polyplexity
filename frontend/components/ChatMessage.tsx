"use client"

import * as React from "react"
import { ChevronsUpDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

export interface ChatMessageProps {
  role: "user" | "assistant"
  content: string
  thoughts?: string[]
  toolCalls?: Array<{ tool: string; input: any }>
  isStreaming?: boolean
}

export function ChatMessage({ 
  role, 
  content, 
  thoughts = [], 
  toolCalls = [],
  isStreaming = false 
}: ChatMessageProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const hasThoughts = thoughts.length > 0 || toolCalls.length > 0

  return (
    <div className={`flex flex-col gap-2 p-4 rounded-lg ${
      role === "user" 
        ? "bg-muted ml-auto max-w-[80%]" 
        : "bg-background border mr-auto max-w-[80%]"
    }`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="text-sm font-semibold mb-1">
            {role === "user" ? "You" : "Assistant"}
          </div>
          <div className="text-sm whitespace-pre-wrap">{content}</div>
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
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
    </div>
  )
}

