import React, { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from 'recharts';
import { format } from 'date-fns';
import { PricePoint, ApprovedMarket } from '../types';
import { fetchPriceHistory } from '../services/polymarketService';

// Polymarket affiliate link constants
const POLYMARKET_BASE_URL = "https://polymarket.com";
const POLYMARKET_AFFILIATE_PARAM = "via=polycommand";

/**
 * Builds a Polymarket event URL with affiliate parameter
 * @param slug - The market event slug
 * @returns Full URL to Polymarket event page with affiliate tracking
 */
const buildEventUrl = (slug: string): string => {
  return `${POLYMARKET_BASE_URL}/event/${slug}?${POLYMARKET_AFFILIATE_PARAM}`;
};

interface PolymarketChartProps {
  market: ApprovedMarket;
}

// Color palette for different lines
const LINE_COLORS = [
  { stroke: '#8b5cf6', fill: '#8b5cf6', fillOpacity: 0.25 }, // Purple
  { stroke: '#3b82f6', fill: '#3b82f6', fillOpacity: 0.25 }, // Blue
  { stroke: '#10b981', fill: '#10b981', fillOpacity: 0.25 }, // Green
  { stroke: '#f59e0b', fill: '#f59e0b', fillOpacity: 0.25 }, // Orange
  { stroke: '#ef4444', fill: '#ef4444', fillOpacity: 0.25 }, // Red
  { stroke: '#06b6d4', fill: '#06b6d4', fillOpacity: 0.25 }, // Cyan
];

interface TokenData {
  clobTokenId: string;
  outcome: string;
  data: PricePoint[];
  color: typeof LINE_COLORS[0];
}

const PolymarketChart: React.FC<PolymarketChartProps> = ({ market }) => {
  const [tokenDataList, setTokenDataList] = useState<TokenData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredClobTokenId, setHoveredClobTokenId] = useState<string | null>(null);
  const [selectedClobTokenId, setSelectedClobTokenId] = useState<string | null>(null);
  const [hoveredPrice, setHoveredPrice] = useState<number | null>(null);
  const [hoveredDate, setHoveredDate] = useState<number | null>(null);
  const [isDescriptionOpen, setIsDescriptionOpen] = useState<boolean>(false);

  const sidebarRef = useRef<HTMLDivElement>(null);
  const tokenRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});
  const isHoveringSidebar = useRef(false);

  // Generate gradient IDs for each token
  const gradientIds = useMemo(() => {
    return market.clobTokenIds.map((_, idx) => `colorPrice-${market.slug}-${idx}`);
  }, [market.slug, market.clobTokenIds.length]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch all clobTokenIds in parallel
      const fetchPromises = market.clobTokenIds.map(async (clobTokenId, index) => {
        try {
          const result = await fetchPriceHistory(clobTokenId);
          const sortedHistory = result.history.sort((a, b) => a.t - b.t);
          return {
            clobTokenId,
            outcome: market.outcomes[index] || `Outcome ${index + 1}`,
            data: sortedHistory,
            color: LINE_COLORS[index % LINE_COLORS.length],
          };
        } catch (e: any) {
          console.error(`Failed to fetch data for ${clobTokenId}:`, e);
          return {
            clobTokenId,
            outcome: market.outcomes[index] || `Outcome ${index + 1}`,
            data: [] as PricePoint[],
            color: LINE_COLORS[index % LINE_COLORS.length],
            error: e.message,
          };
        }
      });

      const results = await Promise.all(fetchPromises);
      setTokenDataList(results.filter(r => r.data.length > 0));
    } catch (e: any) {
      console.error(e);
      setError(e.message || "Failed to load chart data");
    } finally {
      setLoading(false);
    }
  }, [market.clobTokenIds, market.outcomes]);

  // Initial Fetch
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Combine all data points by timestamp for the chart
  const chartData = useMemo(() => {
    if (tokenDataList.length === 0) return [];

    // Get all unique timestamps
    const allTimestamps = new Set<number>();
    tokenDataList.forEach(tokenData => {
      tokenData.data.forEach(point => allTimestamps.add(point.t));
    });

    // Create combined data points
    const sortedTimestamps = Array.from(allTimestamps).sort((a, b) => a - b);
    
    return sortedTimestamps.map(timestamp => {
      const point: any = { t: timestamp };
      tokenDataList.forEach(tokenData => {
        // Find exact match first
        let pricePoint = tokenData.data.find(p => p.t === timestamp);
        
        // If no exact match, find the closest point (for interpolation)
        if (!pricePoint && tokenData.data.length > 0) {
          const sortedData = [...tokenData.data].sort((a, b) => a.t - b.t);
          // Find the point before and after this timestamp
          let before: PricePoint | undefined;
          let after: PricePoint | undefined;
          
          for (let i = sortedData.length - 1; i >= 0; i--) {
            if (sortedData[i].t <= timestamp) {
              before = sortedData[i];
              break;
            }
          }
          
          for (let i = 0; i < sortedData.length; i++) {
            if (sortedData[i].t >= timestamp) {
              after = sortedData[i];
              break;
            }
          }
          
          if (before && after) {
            // Linear interpolation
            const ratio = (timestamp - before.t) / (after.t - before.t);
            const interpolatedPrice = before.p + (after.p - before.p) * ratio;
            pricePoint = { t: timestamp, p: interpolatedPrice };
          } else if (before) {
            pricePoint = before;
          } else if (after) {
            pricePoint = after;
          }
        }
        
        if (pricePoint) {
          point[tokenData.clobTokenId] = pricePoint.p;
        }
      });
      return point;
    });
  }, [tokenDataList]);

  // Handle Chart Hover
  const handleMouseMove = useCallback((state: any) => {
    if (isHoveringSidebar.current) return;

    if (state.activePayload && state.activePayload.length > 0) {
      const payload = state.activePayload[0].payload;
      setHoveredDate(payload.t);
      
      // Find which token was hovered (check all token IDs in payload)
      const hoveredToken = tokenDataList.find(tokenData => 
        payload[tokenData.clobTokenId] !== undefined
      );
      
      if (hoveredToken) {
        setHoveredClobTokenId(hoveredToken.clobTokenId);
        setHoveredPrice(payload[hoveredToken.clobTokenId]);
      }
    }
  }, [tokenDataList]);

  const handleMouseLeave = () => {
    setHoveredPrice(null);
    setHoveredDate(null);
    if (!isHoveringSidebar.current) {
      setHoveredClobTokenId(null);
    }
  };

  // Scroll active token into view
  useEffect(() => {
    const activeId = selectedClobTokenId || hoveredClobTokenId;
    if (activeId && tokenRefs.current[activeId] && sidebarRef.current && !isHoveringSidebar.current) {
      tokenRefs.current[activeId]?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'nearest',
      });
    }
  }, [selectedClobTokenId, hoveredClobTokenId]);

  // Calculate current price for display
  const displayPrice = useMemo(() => {
    if (hoveredPrice !== null) return hoveredPrice;
    if (tokenDataList.length === 0) return 0;
    const firstToken = tokenDataList[0];
    if (firstToken.data.length === 0) return 0;
    return firstToken.data[firstToken.data.length - 1].p;
  }, [hoveredPrice, tokenDataList]);

  // Calculate chart min/max
  const yDomain = useMemo(() => {
    if (chartData.length === 0) return [0, 1];
    const allPrices: number[] = [];
    chartData.forEach(point => {
      tokenDataList.forEach(tokenData => {
        const price = point[tokenData.clobTokenId];
        if (price !== undefined) {
          allPrices.push(price);
        }
      });
    });
    if (allPrices.length === 0) return [0, 1];
    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const padding = (max - min) * 0.15;
    return [Math.max(0, min - padding), Math.min(1, max + padding)];
  }, [chartData, tokenDataList]);

  return (
    <div className="flex flex-col w-full h-[350px] bg-white border border-border rounded-xl shadow-sm overflow-hidden ring-1 ring-border/50">
      
      {/* 1. Header Section */}
      <div className="flex-none px-6 py-5 border-b border-border bg-white flex justify-between items-end z-10">
        <div className="flex-1 min-w-0">
          <h2 className="text-primary text-[10px] uppercase font-bold tracking-widest mb-1.5 flex items-center gap-2">
            Polymarket Insight
            {loading && <span className="w-2 h-2 rounded-full bg-primary animate-ping" />}
          </h2>
          <a
            href={buildEventUrl(market.eventSlug)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xl font-bold text-foreground tracking-tight leading-tight truncate hover:text-primary hover:underline transition-colors cursor-pointer block"
            title={`View on Polymarket: ${market.question}`}
          >
            {market.question}
          </a>
        </div>
        <div className="flex items-end gap-6 ml-4">
           <div className="text-right">
            <div className="text-muted-foreground text-xs mb-1 font-mono">
              {hoveredDate ? format(new Date(hoveredDate * 1000), 'MMM d, yyyy h:mm a') : 'Current Value'}
            </div>
            <div className={`text-3xl font-mono font-bold text-foreground tracking-tight`}>
              {(displayPrice * 100).toFixed(1)}¢
            </div>
          </div>
          
          <button 
            onClick={loadData}
            disabled={loading}
            className="mb-1 p-2 rounded-lg hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh Data"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={loading ? 'animate-spin' : ''}>
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
              <path d="M16 21h5v-5"/>
            </svg>
          </button>
        </div>
      </div>

      {/* 2. Main Content Area (Fixed Height Flex Container) */}
      <div className="flex-1 flex min-h-0">
        
        {/* Left: Chart Area */}
        <div className="w-[70%] h-full relative border-r border-border bg-white p-2">
          {error ? (
             <div className="h-full flex flex-col items-center justify-center text-red-500">
               <span className="font-semibold">Error Loading Data</span>
               <span className="text-xs mt-1">{error}</span>
             </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                margin={{ top: 20, right: 20, left: 0, bottom: 20 }}
              >
                <defs>
                  {tokenDataList.map((tokenData, idx) => (
                    <linearGradient key={tokenData.clobTokenId} id={gradientIds[idx]} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={tokenData.color.stroke} stopOpacity={tokenData.color.fillOpacity} />
                      <stop offset="95%" stopColor={tokenData.color.stroke} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f4f4f5" />
                <XAxis 
                  dataKey="t" 
                  tickFormatter={(unix) => format(new Date(unix * 1000), 'MMM d')}
                  stroke="#d4d4d8"
                  tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'Inter' }}
                  minTickGap={50}
                  axisLine={false}
                  tickLine={false}
                  dy={10}
                />
                <YAxis 
                  domain={yDomain} 
                  hide={false}
                  orientation="right"
                  stroke="#d4d4d8"
                  tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'Inter' }}
                  tickFormatter={(val) => `${(val * 100).toFixed(0)}¢`}
                  axisLine={false}
                  tickLine={false}
                  dx={-5}
                />
                <Tooltip
                  content={() => null} 
                  cursor={{ stroke: '#8b5cf6', strokeWidth: 1.5, strokeDasharray: '4 4' }}
                />
                {tokenDataList.map((tokenData, idx) => {
                  const isHovered = hoveredClobTokenId === tokenData.clobTokenId;
                  const isSelected = selectedClobTokenId === tokenData.clobTokenId;
                  const isActive = isHovered || isSelected;
                  const strokeWidth = isActive ? 5 : 2;
                  const strokeOpacity = isActive ? 1 : 0.4;
                  
                  return (
                    <Area
                      key={tokenData.clobTokenId}
                      type="monotone"
                      dataKey={tokenData.clobTokenId}
                      stroke={tokenData.color.stroke}
                      strokeWidth={strokeWidth}
                      fillOpacity={isActive ? tokenData.color.fillOpacity * 2 : tokenData.color.fillOpacity * 0.5}
                      fill={`url(#${gradientIds[idx]})`}
                      isAnimationActive={true}
                      animationDuration={1000}
                      strokeOpacity={strokeOpacity}
                      connectNulls={true}
                      style={isActive ? { filter: 'drop-shadow(0 0 4px ' + tokenData.color.stroke + ')' } : {}}
                    />
                  );
                })}
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Right: Market Data (Scrollable) */}
        <div 
          className="w-[30%] flex flex-col h-full bg-white"
          onMouseEnter={() => isHoveringSidebar.current = true}
          onMouseLeave={() => isHoveringSidebar.current = false}
        >
          {/* Static Header */}
          <div className="px-5 py-4 border-b border-border bg-white shrink-0">
             <h3 className="text-sm font-semibold text-foreground">Market Data</h3>
             <p className="text-xs text-muted-foreground mt-0.5">Outcomes and details</p>
          </div>
          
          {/* Scrollable List */}
          <div 
            ref={sidebarRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar"
          >
            {/* Market Description Dropdown */}
            {market.description && (
              <div className="rounded-lg bg-muted/30 border border-border/50 overflow-hidden">
                <button
                  onClick={() => setIsDescriptionOpen(!isDescriptionOpen)}
                  className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/40 transition-colors"
                >
                  <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider">
                    Market Rules
                  </h4>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className={`text-muted-foreground transition-transform duration-200 ${
                      isDescriptionOpen ? 'rotate-180' : ''
                    }`}
                  >
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                </button>
                <div
                  className={`overflow-hidden transition-all duration-300 ease-in-out ${
                    isDescriptionOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
                  }`}
                >
                  <div className="px-4 pb-4 pt-2">
                    <p className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed">
                      {market.description}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Outcomes/Token Data */}
            {tokenDataList.map((tokenData) => {
              const isHovered = hoveredClobTokenId === tokenData.clobTokenId;
              const isSelected = selectedClobTokenId === tokenData.clobTokenId;
              const isActive = isHovered || isSelected;
              
              const currentPrice = tokenData.data.length > 0 
                ? tokenData.data[tokenData.data.length - 1].p 
                : 0;
              
              const outcomeIndex = market.clobTokenIds.indexOf(tokenData.clobTokenId);
              const outcomePrice = outcomeIndex >= 0 && market.outcomePrices[outcomeIndex] 
                ? parseFloat(market.outcomePrices[outcomeIndex]) 
                : currentPrice;
              
              return (
                <div
                  key={tokenData.clobTokenId}
                  // @ts-ignore
                  ref={(el) => (tokenRefs.current[tokenData.clobTokenId] = el)}
                  className={`
                    relative px-5 py-4 rounded-2xl transition-all duration-300 ease-out cursor-pointer
                    ${isActive 
                      ? 'bg-muted/70 shadow-lg border-2 border-border' 
                      : 'bg-white hover:bg-muted/30 border border-transparent'}
                  `}
                  onMouseEnter={() => {
                    setHoveredClobTokenId(tokenData.clobTokenId);
                    if (tokenData.data.length > 0) {
                      const latest = tokenData.data[tokenData.data.length - 1];
                      setHoveredPrice(latest.p);
                    }
                  }}
                  onMouseLeave={() => {
                    if (!isHoveringSidebar.current) {
                      setHoveredClobTokenId(null);
                    }
                  }}
                  onClick={() => {
                    // If clicking the already selected item, deselect it
                    // Otherwise, select this one (automatically deselects any other)
                    if (selectedClobTokenId === tokenData.clobTokenId) {
                      setSelectedClobTokenId(null);
                    } else {
                      setSelectedClobTokenId(tokenData.clobTokenId);
                    }
                  }}
                >
                  {/* Color Indicator Bar */}
                  {isActive && (
                     <div 
                       className="absolute left-0 top-3 bottom-3 w-[5px] rounded-r-full shadow-sm"
                       style={{ backgroundColor: tokenData.color.stroke }}
                     /> 
                  )}

                  <div className="flex justify-between items-baseline mb-2">
                    <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
                      {tokenData.outcome}
                    </span>
                    {isActive && (
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: tokenData.color.stroke }}
                      />
                    )}
                  </div>
                  
                  <div className="space-y-1">
                    <div className="text-lg font-mono font-bold text-foreground">
                      {(outcomePrice * 100).toFixed(1)}¢
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Current: {(currentPrice * 100).toFixed(1)}¢
                    </div>
                    <div className="text-[10px] font-mono text-muted-foreground mt-2">
                      {tokenData.clobTokenId.slice(0, 8)}...
                    </div>
                  </div>
                </div>
              );
            })}
             
            {tokenDataList.length === 0 && !loading && (
               <div className="text-center text-muted-foreground text-sm mt-10 p-4">
                 No market data available.
               </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default PolymarketChart;
