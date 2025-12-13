import React, { useRef, useEffect } from 'react';
import { Message } from '../types';
import { MessageBubble } from './MessageBubble';

interface ChatInterfaceProps {
  messages: Message[];
  isGenerating: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ messages, isGenerating }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom only when main content updates (not sources/reasoning)
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    // Only scroll when content changes, not when sources or reasoning update
    if (bottomRef.current && lastMessage?.content) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, messages[messages.length - 1]?.content]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8 scroll-smooth">
      <div className="max-w-4xl mx-auto min-h-full">
        
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((msg, index) => (
            <MessageBubble 
              key={msg.id} 
              message={msg} 
              isLast={index === messages.length - 1} 
            />
          ))
        )}
        
        {/* Spacer for sticky input */}
        <div className="h-32" ref={bottomRef} />
      </div>
    </div>
  );
};

const EmptyState = () => (
  <div className="flex flex-col items-center justify-center h-full pt-20 text-center opacity-0 animate-in fade-in zoom-in duration-700">
    <div className="w-16 h-16 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mb-6">
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    </div>
    <h1 className="text-3xl font-bold tracking-tight mb-2">Where knowledge begins</h1>
    <p className="text-muted-foreground max-w-md">
      Ask anything. I will research, think through the problem, and provide a comprehensive answer.
    </p>
  </div>
);