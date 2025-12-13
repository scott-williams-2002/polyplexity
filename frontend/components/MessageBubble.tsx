import React, { useEffect, useState, useRef } from 'react';
import { Message } from '../types';
import { SourcesGrid } from './SourcesGrid';
import { ReasoningAccordion } from './ReasoningAccordion';
import { MarketChartsContainer } from './MarketChartsContainer';
import { cn } from '../lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageBubbleProps {
  message: Message;
  isLast: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isLast }) => {
  const isUser = message.role === 'user';
  
  // Auto-collapse reasoning when answer starts streaming, but keep open during 'reasoning' stage
  const [isReasoningOpen, setIsReasoningOpen] = useState(true);
  
  // Loading messages for Polymarket data
  const loadingMessages = [
    "Analyzing markets...",
    "Fetching market data...",
    "Preparing market insights...",
  ];
  const [currentLoadingMessageIndex, setCurrentLoadingMessageIndex] = useState(0);
  
  // Detect if we're waiting for Polymarket data
  const isWaitingForPolymarket = 
    message.finalReportComplete && 
    !message.polymarketBlurb && 
    (!message.approvedMarkets || message.approvedMarkets.length === 0);
  
  // Rotate loading messages
  useEffect(() => {
    if (isWaitingForPolymarket) {
      const interval = setInterval(() => {
        setCurrentLoadingMessageIndex((prev) => (prev + 1) % loadingMessages.length);
      }, 2000); // Change message every 2 seconds
      
      return () => clearInterval(interval);
    }
  }, [isWaitingForPolymarket, loadingMessages.length]);

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
      <div className="flex justify-end mb-8 px-2 md:px-0">
        <div className="bg-muted/50 text-foreground px-4 md:px-5 py-3 rounded-2xl max-w-[85%] md:max-w-[80%] text-sm md:text-base sm:text-lg">
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
    <div className="flex flex-col mb-10 w-full max-w-full md:max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500 px-2 md:px-0">
      
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
                      <table className="min-w-full border-collapse border border-border table-auto">
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

      </div>

      {/* Loading messages while waiting for Polymarket data */}
      {isWaitingForPolymarket && (
        <div className="mt-6 flex items-center gap-2 text-purple-400/80">
          <span className="w-2 h-2 bg-purple-400/60 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
          <span className="w-2 h-2 bg-purple-400/60 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
          <span className="w-2 h-2 bg-purple-400/60 rounded-full animate-bounce"></span>
          <span className="text-sm font-medium ml-2">{loadingMessages[currentLoadingMessageIndex]}</span>
        </div>
      )}

      {/* Polymarket Blurb - Displayed above charts */}
      {message.polymarketBlurb && (
        <div className="mt-6 px-4 py-3 rounded-lg bg-muted/30 border-2 border-purple-500/30">
          <h3 className="text-sm font-semibold text-purple-400 mb-2">Polymarket Agent Suggestions ...</h3>
          <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none text-foreground">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0 break-words">{children}</p>,
                strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary/80 break-words">
                    {children}
                  </a>
                ),
              }}
            >
              {message.polymarketBlurb}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* Market Charts Container - Rendered beneath AI response */}
      {message.approvedMarkets && message.approvedMarkets.length > 0 && (
        <div className="mt-6">
          <MarketChartsContainer markets={message.approvedMarkets} />
        </div>
      )}
    </div>
  );
};
