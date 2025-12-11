import React, { useEffect, useState, useRef } from 'react';
import { Message } from '../types';
import { SourcesGrid } from './SourcesGrid';
import { ReasoningAccordion } from './ReasoningAccordion';
import { cn } from '../lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, RefreshCw, ThumbsUp, ThumbsDown } from './ui/Icons';

interface MessageBubbleProps {
  message: Message;
  isLast: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isLast }) => {
  const isUser = message.role === 'user';
  
  // Auto-collapse reasoning when answer starts streaming, but keep open during 'reasoning' stage
  const [isReasoningOpen, setIsReasoningOpen] = useState(true);

  // Compute sticky positioning on every render (which happens on every stream event)
  // Check multiple conditions: stage, isStreaming, and finalReportComplete flag
  const shouldBeSticky = message.stage !== 'completed' && message.isStreaming !== false && message.finalReportComplete !== true;

  useEffect(() => {
    // If we moved from reasoning to answering/completed, collapse it
    if (message.stage === 'answering' || message.stage === 'completed') {
      setIsReasoningOpen(false);
    }
    // If we are currently reasoning, ensure it's open
    if (message.stage === 'reasoning') {
      setIsReasoningOpen(true);
    }
  }, [message.stage]);

  if (isUser) {
    return (
      <div className="flex justify-end mb-8">
        <div className="bg-muted/50 text-foreground px-5 py-3 rounded-2xl max-w-[80%] text-base sm:text-lg">
          {message.content}
        </div>
      </div>
    );
  }

  const contentRef = useRef<HTMLDivElement>(null);

  // Auto-scroll content area when streaming
  useEffect(() => {
    if (message.isStreaming && message.stage === 'answering' && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [message.content, message.isStreaming, message.stage]);

  return (
    <div className="flex flex-col mb-10 w-full max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header Section: Reasoning + Sources (Fixed during streaming, scrollable when completed) */}
      <div className={`${shouldBeSticky ? 'sticky top-0 z-10' : ''} bg-background/95 backdrop-blur-sm border-b border-border pb-4 mb-4 flex-shrink-0`}>
        {/* 1. Reasoning Section */}
        {message.reasoning && message.reasoning.trim() && (
          <ReasoningAccordion 
            reasoning={message.reasoning} 
            isOpen={isReasoningOpen}
            isStreaming={message.stage === 'reasoning' || message.stage === 'searching'}
            onToggle={() => setIsReasoningOpen(!isReasoningOpen)}
          />
        )}

        {/* 2. Sources Section */}
        {message.sources && message.sources.length > 0 && (
          <SourcesGrid 
            sources={message.sources} 
            isStreaming={message.stage === 'searching'} 
          />
        )}
      </div>

      {/* Scrollable Content Section */}
      <div 
        ref={contentRef}
        className={`flex-1 overflow-y-auto scroll-smooth ${shouldBeSticky ? 'max-h-[60vh]' : ''}`}
      >
        <div className="relative group">
          {/* Placeholder during pure searching/thinking if no content yet */}
          {!message.content && message.stage !== 'completed' && message.stage !== 'answering' ? (
               <div className="flex items-center gap-2 text-muted-foreground py-4">
                  <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"></span>
               </div>
          ) : (
            <div className="prose prose-neutral dark:prose-invert max-w-none text-foreground leading-relaxed">
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
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer Actions (Only show when some content exists) */}
        {(message.content || message.stage === 'completed') && (
          <div className="flex items-center gap-2 mt-4 pt-2">
            <ActionButton icon={<Copy className="w-4 h-4" />} label="Copy" />
            <ActionButton icon={<RefreshCw className="w-4 h-4" />} label="Rewrite" />
            <div className="flex-grow" />
            <ActionButton icon={<ThumbsUp className="w-4 h-4" />} />
            <ActionButton icon={<ThumbsDown className="w-4 h-4" />} />
          </div>
        )}
      </div>
    </div>
  );
};

const ActionButton = ({ icon, label }: { icon: React.ReactNode, label?: string }) => (
  <button className="flex items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors">
    {icon}
    {label && <span>{label}</span>}
  </button>
);