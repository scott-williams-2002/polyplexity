import React, { useState, useRef, useEffect } from 'react';
import { Send } from './ui/Icons';
import { cn } from '../lib/utils';

interface InputAreaProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export const InputArea: React.FC<InputAreaProps> = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div className="sticky bottom-0 bg-background/80 backdrop-blur-md border-t border-border/50 pb-6 pt-2 px-4 z-50">
      <div className="max-w-3xl mx-auto relative">
        <div className={cn(
          "relative flex flex-col bg-muted/30 border border-input rounded-xl shadow-sm transition-all duration-200 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/50",
          disabled && "opacity-50 cursor-not-allowed"
        )}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            disabled={disabled}
            className="w-full bg-transparent border-none focus:ring-0 resize-none py-4 px-4 min-h-[60px] max-h-[200px] text-base outline-none disabled:cursor-not-allowed"
            rows={1}
          />
          
          <div className="flex items-center justify-end px-2 pb-2">
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || disabled}
              className={cn(
                "p-2 rounded-full transition-all duration-200 flex items-center justify-center",
                input.trim() && !disabled
                  ? "bg-primary text-primary-foreground hover:bg-primary/90 shadow-md"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
              )}
            >
              <Send className="w-4 h-4 ml-0.5" />
            </button>
          </div>
        </div>
        
        <div className="text-center mt-2">
          <span className="text-[10px] text-muted-foreground">
            AI can make mistakes. Please double check responses.
          </span>
        </div>
      </div>
    </div>
  );
};
