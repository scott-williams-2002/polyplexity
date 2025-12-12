import { useState, useCallback, useEffect } from "react";
import { fetchThreads, deleteThread, ThreadInfo } from "../lib/api";

interface UseThreadsProps {
  refreshTrigger?: number;
}

export function useThreads({ refreshTrigger = 0 }: UseThreadsProps = {}) {
  const [threads, setThreads] = useState<ThreadInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadThreads = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchThreads();
      setThreads(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load threads";
      setError(errorMessage);
      console.error("Failed to load threads:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDeleteThread = useCallback(async (threadId: string) => {
    try {
      await deleteThread(threadId);
      // Remove the thread from local state
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
      return true;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to delete thread";
      setError(errorMessage);
      console.error("Failed to delete thread:", err);
      return false;
    }
  }, []);

  const refreshThreads = useCallback(() => {
    loadThreads();
  }, [loadThreads]);

  // Initial load on mount
  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  // Refresh when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger > 0) {
      loadThreads();
    }
  }, [refreshTrigger, loadThreads]);

  return {
    threads,
    loading,
    error,
    loadThreads,
    deleteThread: handleDeleteThread,
    refreshThreads,
  };
}

