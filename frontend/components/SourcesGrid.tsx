import React, { useEffect, useRef, useState } from 'react';
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
            <TooltipSourceCard key={source.id} source={source} idx={idx} />
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

// Separate component for tooltip functionality
const TooltipSourceCard: React.FC<{ source: ReferenceSource; idx: number }> = ({ source, idx }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const titleRef = useRef<HTMLDivElement>(null);
  const [isOverflowing, setIsOverflowing] = useState(false);

  useEffect(() => {
    // Check if text is overflowing
    if (titleRef.current) {
      setIsOverflowing(titleRef.current.scrollHeight > titleRef.current.clientHeight);
    }
  }, [source.title]);

  const tooltipText = `${source.title}\n${source.domain}\n${source.url}`;

  return (
    <div className="relative group">
      <motion.a
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3, delay: idx * 0.05 }}
        className="flex flex-col p-3 min-h-[96px] min-w-[200px] max-w-[200px] rounded-lg border border-border bg-card hover:bg-muted/50 transition-colors cursor-pointer snap-start flex-shrink-0"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        title={tooltipText}
      >
        <div className="text-xs text-muted-foreground truncate w-full mb-1">
          {source.domain}
        </div>
        <div 
          ref={titleRef}
          className="text-sm font-medium leading-snug line-clamp-2 group-hover:text-primary transition-colors flex-1"
          style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            minHeight: '2.5rem', // Ensure consistent height for 2 lines
          }}
        >
          {source.title}
        </div>
      </motion.a>
      
      {/* Custom tooltip for better styling */}
      {showTooltip && (isOverflowing || source.title.length > 50) && (
        <div className="absolute z-50 px-3 py-2 text-xs bg-popover border border-border rounded-md shadow-lg pointer-events-none bottom-full left-1/2 transform -translate-x-1/2 mb-2 max-w-xs">
          <div className="font-medium mb-1">{source.title}</div>
          <div className="text-muted-foreground text-[10px]">{source.domain}</div>
          <div className="text-muted-foreground text-[10px] truncate mt-1">{source.url}</div>
          {/* Tooltip arrow */}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-px">
            <div className="w-2 h-2 bg-popover border-r border-b border-border transform rotate-45"></div>
          </div>
        </div>
      )}
    </div>
  );
};