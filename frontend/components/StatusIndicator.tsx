"use client"

import * as React from "react"

export interface StatusIndicatorProps {
  status: string | null
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  if (!status) {
    return null
  }

  return (
    <div className="text-sm text-muted-foreground animate-pulse">
      {status}
    </div>
  )
}

