"use client"

import * as React from "react"
import { MessageSquare, Plus, Trash2 } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { fetchThreads, deleteThread, ThreadInfo } from "@/lib/api"

interface ThreadSidebarProps {
  activeThreadId: string | null
  onThreadSelect: (threadId: string | null) => void
  onNewThread: () => void
  refreshTrigger?: number // Optional: increment this to trigger refresh
}

export function ThreadSidebar({
  activeThreadId,
  onThreadSelect,
  onNewThread,
  refreshTrigger = 0,
}: ThreadSidebarProps) {
  const [threads, setThreads] = React.useState<ThreadInfo[]>([])
  const [loading, setLoading] = React.useState(true)
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false)
  const [threadToDelete, setThreadToDelete] = React.useState<string | null>(null)
  const [deleting, setDeleting] = React.useState(false)

  const loadThreads = React.useCallback(async () => {
    try {
      setLoading(true)
      const data = await fetchThreads()
      setThreads(data)
    } catch (error) {
      console.error("Failed to load threads:", error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load on mount
  React.useEffect(() => {
    loadThreads()
  }, [loadThreads])

  // Refresh when refreshTrigger changes (triggered by parent after message sent)
  React.useEffect(() => {
    if (refreshTrigger > 0) {
      loadThreads()
    }
  }, [refreshTrigger, loadThreads])

  const handleDeleteClick = (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation() // Prevent thread selection
    setThreadToDelete(threadId)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!threadToDelete) return

    try {
      setDeleting(true)
      
      // Optimistically remove thread from local state
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadToDelete))
      
      // If deleted thread was active, clear it
      if (activeThreadId === threadToDelete) {
        onThreadSelect(null)
      }
      
      // Delete on backend
      await deleteThread(threadToDelete)
      
      // Small delay to ensure backend has processed deletion, then refresh
      await new Promise((resolve) => setTimeout(resolve, 100))
      await loadThreads()
      
      setDeleteDialogOpen(false)
      setThreadToDelete(null)
    } catch (error) {
      console.error("Failed to delete thread:", error)
      // Reload threads to restore state if deletion failed
      await loadThreads()
      alert(`Failed to delete thread: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setDeleting(false)
    }
  }

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false)
    setThreadToDelete(null)
  }

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <div className="flex items-center gap-2">
                <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <MessageSquare className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-medium">Chat</span>
                  <span className="text-xs text-muted-foreground">
                    {threads.length} {threads.length === 1 ? "thread" : "threads"}
                  </span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <div className="px-2 py-2">
            <Button
              onClick={onNewThread}
              className="w-full"
              size="sm"
              variant="outline"
            >
              <Plus className="size-4 mr-2" />
              New Chat
            </Button>
          </div>
          <SidebarMenu>
            {loading ? (
              <SidebarMenuItem>
                <div className="px-2 py-4 text-sm text-muted-foreground">
                  Loading threads...
                </div>
              </SidebarMenuItem>
            ) : threads.length === 0 ? (
              <SidebarMenuItem>
                <div className="px-2 py-4 text-sm text-muted-foreground">
                  No threads yet. Start a new chat!
                </div>
              </SidebarMenuItem>
            ) : (
              threads.map((thread) => (
                <SidebarMenuItem key={thread.thread_id}>
                  <div className="flex items-center gap-1 w-full group">
                    <SidebarMenuButton
                      asChild
                      isActive={activeThreadId === thread.thread_id}
                      className="flex-1"
                    >
                      <button
                        onClick={() => onThreadSelect(thread.thread_id)}
                        className="w-full text-left"
                      >
                        <div className="flex flex-col gap-1">
                          <div className="text-sm font-medium line-clamp-1">
                            {thread.name || thread.last_message || "New thread"}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {thread.message_count} {thread.message_count === 1 ? "message" : "messages"}
                          </div>
                        </div>
                      </button>
                    </SidebarMenuButton>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                      onClick={(e) => handleDeleteClick(e, thread.thread_id)}
                      aria-label={`Delete thread ${thread.thread_id}`}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                </SidebarMenuItem>
              ))
            )}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
      
      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Thread</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this conversation thread? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleDeleteCancel}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Sidebar>
  )
}

