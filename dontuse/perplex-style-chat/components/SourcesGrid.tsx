import React, { useEffect, useRef } from 'react';
import { ReferenceSource } from '../types';
import { Globe } from './ui/Icons';
import { motion } from 'framer-motion';

interface SourcesGridProps {
  sources: ReferenceSource[];
  isStreaming: boolean;
}

export const SourcesGrid: React.FC<SourcesGridProps> = ({ sources, isStreaming }) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to right when new sources are added
  useEffect(() => {
    if (scrollContainerRef.current && sources.length > 0) {
      scrollContainerRef.current.scrollTo({
        left: scrollContainerRef.current.scrollWidth,
        behavior: 'smooth'
      });
    }
  }, [sources.length]);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        <Globe className="w-3 h-3" />
        <span>Sources</span>
      </div>
      
      {/* Horizontal scrollable carousel */}
      <div 
        ref={scrollContainerRef}
        className="overflow-x-auto scroll-smooth snap-x snap-mandatory scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent"
        style={{
          scrollbarWidth: 'thin',
          msOverflowStyle: 'auto'
        }}
      >
        <div className="flex gap-2 pb-2" style={{ minWidth: 'max-content' }}>
          {sources.map((source, idx) => (
            <motion.a
              key={source.id}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.05 }}
              className="flex flex-col justify-between p-3 h-24 min-w-[200px] max-w-[200px] rounded-lg border border-border bg-card hover:bg-muted/50 transition-colors cursor-pointer group snap-start flex-shrink-0"
            >
              <div className="text-xs text-muted-foreground truncate w-full mb-1">
                {source.domain}
              </div>
              <div className="text-sm font-medium leading-tight line-clamp-2 group-hover:text-primary transition-colors">
                {source.title}
              </div>
              <div className="flex items-center gap-1 mt-2">
                 <div className="w-4 h-4 rounded-full bg-muted flex items-center justify-center text-[10px] text-muted-foreground">
                   {idx + 1}
                 </div>
              </div>
            </motion.a>
          ))}
          
          {/* Skeleton Loader for pending sources if explicitly searching */}
          {isStreaming && sources.length < 4 && (
            <div className="h-24 min-w-[200px] max-w-[200px] rounded-lg border border-border border-dashed flex items-center justify-center bg-muted/20 animate-pulse snap-start flex-shrink-0">
              <span className="text-xs text-muted-foreground">Searching...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};