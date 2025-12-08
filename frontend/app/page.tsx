"use client"

import * as React from "react"
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { ThreadSidebar } from "@/components/ThreadSidebar"
import { ChatInterface } from "@/components/ChatInterface"

export default function Home() {
  const [activeThreadId, setActiveThreadId] = React.useState<string | null>(null)
  const [refreshKey, setRefreshKey] = React.useState(0)

  const handleThreadSelect = (threadId: string | null) => {
    setActiveThreadId(threadId)
  }

  const handleNewThread = () => {
    setActiveThreadId(null)
  }

  const handleMessageSent = () => {
    // Trigger refresh of thread list
    setRefreshKey((prev) => prev + 1)
  }

  return (
    <div className="h-screen flex flex-col">
      <SidebarProvider>
        <ThreadSidebar
          refreshTrigger={refreshKey}
          activeThreadId={activeThreadId}
          onThreadSelect={handleThreadSelect}
          onNewThread={handleNewThread}
        />
        <SidebarInset className="flex flex-col h-full">
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <div className="flex-1">
              <h1 className="text-lg font-semibold">Chat</h1>
            </div>
          </header>
          <div className="flex flex-1 flex-col overflow-hidden min-h-0">
            <ChatInterface
              threadId={activeThreadId}
              onThreadIdChange={handleThreadSelect}
              onMessageSent={handleMessageSent}
            />
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  )
}
