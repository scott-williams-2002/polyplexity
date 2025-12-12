import React, { useState, useCallback, useEffect, useRef } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { InputArea } from './components/InputArea';
import { Message } from './types';
import { generateId } from './lib/utils';
import { Library, MessageSquare, Trash2 } from './components/ui/Icons';
import { useChatStream } from './hooks/useChatStream';
import { useThreads } from './hooks/useThreads';
import { getThreadHistory } from './lib/api';
import { apiMessageToViteMessage, sourceToReferenceSource, parseMarkdownLinks } from './lib/adapters';

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const loadedThreadIdRef = useRef<string | null>(null);

  const {
    isStreaming,
    streamingContent,
    reasoning,
    sources,
    stage,
    finalReportComplete,
    approvedMarkets,
    polymarketBlurb,
    startStreaming,
    reset: resetStream,
  } = useChatStream({
    threadId,
    onThreadIdChange: setThreadId,
    onMessageSent: () => {
      setRefreshTrigger((prev) => prev + 1);
    },
  });

  const { threads, loading: threadsLoading, deleteThread: handleDeleteThread } = useThreads({
    refreshTrigger,
  });

  // Load thread history when threadId changes
  useEffect(() => {
    if (!threadId) {
      setMessages([]);
      loadedThreadIdRef.current = null;
      return;
    }

    if (threadId !== loadedThreadIdRef.current) {
      setMessages([]);
      loadedThreadIdRef.current = null;

      const loadHistory = async () => {
        try {
          const history = await getThreadHistory(threadId);
          const formattedMessages: Message[] = history.map((msg, index) =>
            apiMessageToViteMessage(msg, `history-${threadId}-${index}`)
          );
          setMessages(formattedMessages);
          loadedThreadIdRef.current = threadId;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : "Failed to load thread history";
          console.error("Failed to load thread history:", errorMessage);
          // Don't set loadedThreadIdRef to null on error so we don't retry infinitely
          // Only set to null if it's a 404 (thread not found)
          if (errorMessage.includes('not found')) {
            loadedThreadIdRef.current = null;
          }
        }
      };

      loadHistory();
    }
  }, [threadId]);

  // Update messages with streaming content - run on every change
  // Pattern matches Next.js frontend: update whenever streaming state changes
  // to ensure execution trace, sources, and content update incrementally
  useEffect(() => {
    if (isStreaming) {
      // Update while streaming - always update to show execution trace even if content is empty
      setMessages((prev) => {
        const updated = [...prev];
        let foundStreaming = false;
        
        // Find the last assistant message that's streaming
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === "assistant" && updated[i].isStreaming) {
            // Merge new sources with existing ones, preserving existing IDs
            const existingSources = updated[i].sources || [];
            const existingSourcesMap = new Map(existingSources.map(s => [s.url, s]));
            
            const referenceSources = sources.map(sourceToReferenceSource);
            // Parse markdown links from reasoning and merge with existing sources
            const parsedLinks = reasoning ? parseMarkdownLinks(reasoning) : [];
            const allSources = [...referenceSources, ...parsedLinks];
            
            // Merge: preserve existing source IDs, use new ones for new URLs
            const mergedSources = allSources.map(newSource => {
              const existing = existingSourcesMap.get(newSource.url);
              if (existing) {
                // Preserve existing source (with its ID) but update title/domain if changed
                return { ...existing, title: newSource.title, domain: newSource.domain };
              }
              return newSource;
            });
            
            // Deduplicate by URL (keep first occurrence)
            const uniqueSources = mergedSources.filter((source, index, self) => 
              index === self.findIndex(s => s.url === source.url)
            );
            
            updated[i] = {
              ...updated[i],
              content: streamingContent || updated[i].content,
              reasoning: reasoning || undefined, // Always update, even if empty, to show incremental updates
              sources: uniqueSources.length > 0 ? uniqueSources : updated[i].sources,
              approvedMarkets: approvedMarkets.length > 0 ? approvedMarkets : updated[i].approvedMarkets,
              polymarketBlurb: polymarketBlurb || updated[i].polymarketBlurb,
              stage: stage || updated[i].stage || "searching",
              isStreaming: true,
              finalReportComplete: finalReportComplete || updated[i].finalReportComplete || false,
            };
            foundStreaming = true;
            break;
          }
        }
        
        // If no streaming message found, add one (even if content is empty, to show trace)
        if (!foundStreaming) {
          const referenceSources = sources.map(sourceToReferenceSource);
          // Parse markdown links from reasoning and merge with existing sources
          const parsedLinks = reasoning ? parseMarkdownLinks(reasoning) : [];
          const allSources = [...referenceSources, ...parsedLinks];
          // Deduplicate by URL (keep first occurrence) - stable IDs already handled in adapters
          const uniqueSources = allSources.filter((source, index, self) => 
            index === self.findIndex(s => s.url === source.url)
          );
          
          updated.push({
            id: generateId(),
            role: "assistant",
            content: streamingContent || "",
            reasoning: reasoning || undefined,
            sources: uniqueSources,
            approvedMarkets: approvedMarkets.length > 0 ? approvedMarkets : undefined,
            polymarketBlurb: polymarketBlurb || undefined,
            timestamp: Date.now(),
            stage: stage || "searching",
            isStreaming: true,
            finalReportComplete: false,
          });
        }
        
        return updated;
      });
    } else if (!isStreaming && streamingContent) {
      // Finalize message when streaming completes
      setMessages((prev) => {
        const updated = [...prev];
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === "assistant" && updated[i].isStreaming) {
            // Merge new sources with existing ones, preserving existing IDs
            const existingSources = updated[i].sources || [];
            const existingSourcesMap = new Map(existingSources.map(s => [s.url, s]));
            
            const referenceSources = sources.map(sourceToReferenceSource);
            // Parse markdown links from reasoning and merge with existing sources
            const parsedLinks = reasoning ? parseMarkdownLinks(reasoning) : [];
            const allSources = [...referenceSources, ...parsedLinks];
            
            // Merge: preserve existing source IDs, use new ones for new URLs
            const mergedSources = allSources.map(newSource => {
              const existing = existingSourcesMap.get(newSource.url);
              if (existing) {
                // Preserve existing source (with its ID) but update title/domain if changed
                return { ...existing, title: newSource.title, domain: newSource.domain };
              }
              return newSource;
            });
            
            // Deduplicate by URL (keep first occurrence)
            const uniqueSources = mergedSources.filter((source, index, self) => 
              index === self.findIndex(s => s.url === source.url)
            );
            
            const finalApprovedMarkets = approvedMarkets.length > 0 ? approvedMarkets : updated[i].approvedMarkets;
            const finalPolymarketBlurb = polymarketBlurb || updated[i].polymarketBlurb;
            
            updated[i] = {
              ...updated[i],
              content: streamingContent || updated[i].content,
              reasoning: reasoning || undefined, // Always update reasoning
              sources: uniqueSources,
              approvedMarkets: finalApprovedMarkets,
              polymarketBlurb: finalPolymarketBlurb,
              stage: "completed",
              isStreaming: false,
              finalReportComplete: true,
            };
            break;
          }
        }
        return updated;
      });
      resetStream();
    }
  }, [isStreaming, streamingContent, reasoning, sources, stage, finalReportComplete, approvedMarkets, polymarketBlurb, resetStream]);

  const handleSendMessage = useCallback(
    async (content: string) => {
      // 1. Add User Message
      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content,
        timestamp: Date.now(),
      };

      // 2. Add Placeholder Bot Message
      const botMsgPlaceholder: Message = {
        id: generateId(),
        role: "assistant",
        content: "",
        reasoning: "",
        sources: [],
        timestamp: Date.now(),
        stage: "searching",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, botMsgPlaceholder]);

      // 3. Start Real Streaming
      await startStreaming(content, threadId);
    },
    [threadId, startStreaming]
  );

  const handleNewThread = useCallback(() => {
    setThreadId(null);
    setMessages([]);
    resetStream();
  }, [resetStream]);

  const handleThreadSelect = useCallback((selectedThreadId: string) => {
    setThreadId(selectedThreadId);
  }, []);

  const handleDeleteThreadClick = useCallback(
    async (e: React.MouseEvent, threadIdToDelete: string) => {
      e.stopPropagation();
      if (confirm("Are you sure you want to delete this thread?")) {
        const success = await handleDeleteThread(threadIdToDelete);
        if (success && threadIdToDelete === threadId) {
          setThreadId(null);
          setMessages([]);
        }
      }
    },
    [threadId, handleDeleteThread]
  );

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans">
      
      {/* Sidebar */}
      <aside className="hidden md:flex w-64 flex-col border-r border-border bg-muted/10 p-4">
        <div className="flex items-center gap-2 mb-6 px-2">
           <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
             <Library className="text-primary-foreground w-5 h-5" />
           </div>
           <span className="font-bold text-lg tracking-tight">Perplex-Chat</span>
        </div>
        
        <button
          onClick={handleNewThread}
          className="flex items-center gap-2 w-full px-4 py-3 bg-muted/50 hover:bg-muted text-sm font-medium rounded-full mb-4 transition-colors text-left border border-transparent hover:border-border"
        >
          <div className="w-4 h-4 rounded-full border border-current opacity-60" />
          <span>New Thread</span>
          <span className="ml-auto text-xs opacity-50">Cmd+N</span>
        </button>

        <div className="flex-1 overflow-y-auto">
          <div className="text-xs font-semibold text-muted-foreground mb-3 px-2">Library</div>
          {threadsLoading ? (
            <div className="text-sm text-muted-foreground px-2">Loading threads...</div>
          ) : threads.length === 0 ? (
            <div className="text-sm text-muted-foreground px-2">No threads yet</div>
          ) : (
            <div className="space-y-1">
              {threads.map((thread) => (
                <div
                  key={thread.thread_id}
                  onClick={() => handleThreadSelect(thread.thread_id)}
                  className={`flex items-center gap-3 px-3 py-2 text-sm rounded-md hover:bg-muted cursor-pointer transition-colors group ${
                    threadId === thread.thread_id ? "bg-muted" : ""
                  }`}
                >
                  <MessageSquare className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                  <span className="truncate flex-1 opacity-80 group-hover:opacity-100">
                    {thread.name || thread.last_message || "Untitled Thread"}
                  </span>
                  <button
                    onClick={(e) => handleDeleteThreadClick(e, thread.thread_id)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-muted-foreground/10 rounded"
                  >
                    <Trash2 className="w-3 h-3 text-muted-foreground" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="mt-auto border-t border-border pt-4">
          <div className="flex items-center gap-3 px-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-cyan-400" />
            <div className="text-sm">
              <div className="font-medium">User</div>
              <div className="text-xs text-muted-foreground">Pro Member</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative h-full">
        {/* Header (Mobile) */}
        <header className="md:hidden flex items-center justify-center h-14 border-b border-border bg-background/50 backdrop-blur-sm sticky top-0 z-40">
           <span className="font-semibold">Perplex-Chat</span>
        </header>

        <ChatInterface messages={messages} isGenerating={isStreaming} />
        
        <InputArea onSend={handleSendMessage} disabled={isStreaming} />
      </main>
    </div>
  );
}