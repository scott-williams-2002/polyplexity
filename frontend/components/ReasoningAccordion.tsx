import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, ChevronDown } from './ui/Icons';
import { cn } from '../lib/utils';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ReasoningAccordionProps {
  reasoning: string;
  isOpen: boolean;
  isStreaming: boolean;
  onToggle: () => void;
}

export const ReasoningAccordion: React.FC<ReasoningAccordionProps> = ({ 
  reasoning, 
  isOpen: propIsOpen, 
  isStreaming,
  onToggle 
}) => {
  // We want to auto-scroll the reasoning box if it's streaming and open
  const contentRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isStreaming && propIsOpen && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [reasoning, isStreaming, propIsOpen]);

  if (!reasoning) return null;

  return (
    <div className="mb-4">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors py-2 group select-none"
      >
        <div className={cn(
          "flex items-center justify-center w-5 h-5 rounded bg-muted group-hover:bg-muted/80",
          isStreaming && "animate-pulse text-primary"
        )}>
          <BrainCircuit className="w-3.5 h-3.5" />
        </div>
        <span className="font-medium">
          {isStreaming ? 'Thinking Process' : 'Thought Process'}
        </span>
        <ChevronDown 
          className={cn(
            "w-4 h-4 transition-transform duration-200",
            propIsOpen ? "rotate-180" : "rotate-0"
          )} 
        />
      </button>

      <AnimatePresence initial={false}>
        {propIsOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="pl-2 border-l-2 border-border ml-2.5 my-1">
              <div 
                ref={contentRef}
                className="prose prose-sm dark:prose-invert max-w-none text-muted-foreground max-h-[300px] overflow-y-auto pr-2 custom-scrollbar text-sm"
              >
                 <ReactMarkdown 
                   remarkPlugins={[remarkGfm]}
                   components={{
                     p: ({ children }) => <p className="mb-1 last:mb-0 break-words">{children}</p>,
                     h1: ({ children }) => <h1 className="text-sm font-bold mb-1 mt-2 first:mt-0 break-words">{children}</h1>,
                     h2: ({ children }) => <h2 className="text-sm font-semibold mb-1 mt-2 first:mt-0 break-words">{children}</h2>,
                     h3: ({ children }) => <h3 className="text-xs font-semibold mb-1 mt-1 first:mt-0 break-words">{children}</h3>,
                     ul: ({ children }) => <ul className="list-disc list-inside mb-1 space-y-0.5 break-words">{children}</ul>,
                     ol: ({ children }) => <ol className="list-decimal list-inside mb-1 space-y-0.5 break-words">{children}</ol>,
                     li: ({ children }) => <li className="ml-1 break-words">{children}</li>,
                     code: ({ children, className }) => {
                       const isInline = !className
                       return isInline ? (
                         <code className="bg-muted/50 px-1 py-0.5 rounded text-[10px] font-mono break-words">{children}</code>
                       ) : (
                         <code className={className}>{children}</code>
                       )
                     },
                     pre: ({ children }) => (
                       <pre className="bg-muted/50 p-2 rounded-md overflow-x-auto mb-1 text-[10px] font-mono max-w-full">
                         {children}
                       </pre>
                     ),
                     a: ({ href, children }) => (
                       <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary/80 break-words">
                         {children}
                       </a>
                     ),
                     blockquote: ({ children }) => (
                       <blockquote className="border-l-2 border-muted-foreground/30 pl-2 italic my-1 break-words">
                         {children}
                       </blockquote>
                     ),
                   }}
                 >
                   {reasoning}
                 </ReactMarkdown>
                 {isStreaming && (
                   <span className="inline-block w-2 h-4 ml-1 align-middle bg-primary animate-pulse" />
                 )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};