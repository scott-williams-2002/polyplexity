"use client"

import * as React from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Source } from "@/lib/types"

export interface SourcesProps {
  sources: Source[]
}

export function Sources({ sources }: SourcesProps) {
  if (sources.length === 0) {
    return null
  }

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <div className="text-xs font-semibold text-muted-foreground mb-2">
        Sources:
      </div>
      <div className="flex flex-wrap gap-2">
        {sources.map((source, index) => (
          <a
            key={index}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-muted hover:bg-muted/80 text-primary border border-border transition-colors"
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <span>{children}</span>,
                a: ({ href, children }) => (
                  <span className="text-primary">{children}</span>
                ),
              }}
            >
              {source.markdown}
            </ReactMarkdown>
          </a>
        ))}
      </div>
    </div>
  )
}

