import React, { useEffect, useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { fetchPriceHistory, PriceHistoryPoint } from '../lib/api';

interface PolymarketChartProps {
  clobTokenIds: string[];
  interval?: string;
  height?: number;
}

interface ChartDataPoint {
  timestamp: number;
  date: string;
  [key: string]: number | string; // Dynamic keys for each token ID
}

type TimeWindow = 'hour' | 'day' | 'week' | 'month' | 'year' | 'max';

// Color palette for multiple lines (financial-themed colors)
const CHART_COLORS = [
  '#3b82f6', // Blue
  '#10b981', // Green
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#8b5cf6', // Purple
  '#06b6d4', // Cyan
  '#f97316', // Orange
  '#ec4899', // Pink
];

export const PolymarketChart: React.FC<PolymarketChartProps> = ({
  clobTokenIds,
  interval = 'max',
  height = 100, // Reduced to ~1/4 of original 400px
}) => {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('max');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // Helper function to get ISO week number
  const getWeekNumber = (date: Date): number => {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  };

  // Helper function to get date from ISO week
  const getDateFromISOWeek = (year: number, week: number): Date => {
    const simple = new Date(year, 0, 1 + (week - 1) * 7);
    const dow = simple.getDay();
    const ISOweekStart = simple;
    if (dow <= 4) {
      ISOweekStart.setDate(simple.getDate() - simple.getDay() + 1);
    } else {
      ISOweekStart.setDate(simple.getDate() + 8 - simple.getDay());
    }
    return ISOweekStart;
  };

  // Calculate if time window exceeds data range
  const shouldShowDateInputs = useMemo(() => {
    if (data.length === 0 || timeWindow === 'max') return false;
    
    const now = Date.now() / 1000; // Current time in seconds
    const oldestTimestamp = data[0]?.timestamp || now;
    const dataRangeSeconds = now - oldestTimestamp;
    
    let windowSeconds: number;
    switch (timeWindow) {
      case 'hour':
        windowSeconds = 3600;
        break;
      case 'day':
        windowSeconds = 86400;
        break;
      case 'week':
        windowSeconds = 604800;
        break;
      case 'month':
        windowSeconds = 2592000; // ~30 days
        break;
      case 'year':
        windowSeconds = 31536000; // ~365 days
        break;
      default:
        return false;
    }
    
    // Show date inputs only if time window is smaller than data range
    return windowSeconds < dataRangeSeconds;
  }, [data, timeWindow]);

  // Calculate date range based on time window (backwards from now)
  useEffect(() => {
    if (timeWindow === 'max' || !shouldShowDateInputs) {
      setStartDate('');
      setEndDate('');
      return;
    }

    const now = new Date();
    let start: Date;
    let end: Date = new Date(now);

    switch (timeWindow) {
      case 'hour':
        start = new Date(now);
        start.setHours(now.getHours() - 1);
        break;
      case 'day':
        start = new Date(now);
        start.setDate(now.getDate() - 1);
        break;
      case 'week':
        start = new Date(now);
        start.setDate(now.getDate() - 7);
        break;
      case 'month':
        start = new Date(now);
        start.setMonth(now.getMonth() - 1);
        break;
      case 'year':
        start = new Date(now);
        start.setFullYear(now.getFullYear() - 1);
        break;
      default:
        return;
    }

    // Format dates based on time window
    const formatDate = (date: Date, window: TimeWindow): string => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');

      switch (window) {
        case 'hour':
          return `${year}-${month}-${day}T${hours}:${minutes}`;
        case 'day':
          return `${year}-${month}-${day}`;
        case 'week':
          // For week input, use ISO week format: YYYY-Www
          const weekStart = new Date(date);
          const weekNum = getWeekNumber(weekStart);
          return `${year}-W${String(weekNum).padStart(2, '0')}`;
        case 'month':
          return `${year}-${month}`;
        case 'year':
          return String(year);
        default:
          return '';
      }
    };

    setStartDate(formatDate(start, timeWindow));
    setEndDate(formatDate(end, timeWindow));
  }, [timeWindow, shouldShowDateInputs]);

  // Format X-axis ticks based on time window
  const formatXAxisTick = useMemo(() => {
    return (timestamp: number): string => {
      const date = new Date(timestamp * 1000);
      
      switch (timeWindow) {
        case 'hour':
          return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        case 'day':
          return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        case 'week':
          return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        case 'month':
          const day = date.getDate();
          // Show ticks at day 1, 15, and 30 (or last day of month)
          if (day === 1 || day === 15 || day >= 28) {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
          }
          return '';
        case 'year':
          return date.toLocaleDateString('en-US', { month: 'short' });
        case 'max':
          return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        default:
          return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }
    };
  }, [timeWindow]);

  // Calculate X-axis tick interval based on time window
  const tickInterval = useMemo(() => {
    if (data.length === 0) return undefined;
    
    const dataLength = data.length;
    let desiredTicks: number;
    
    switch (timeWindow) {
      case 'hour':
        desiredTicks = 6; // Show 6 ticks for an hour
        break;
      case 'day':
        desiredTicks = 12; // Show 12 ticks for a day
        break;
      case 'week':
        desiredTicks = 7; // Show 7 ticks for a week
        break;
      case 'month':
        desiredTicks = 3; // Show 3 ticks (day 1, 15, 30)
        break;
      case 'year':
        desiredTicks = 12; // Show 12 ticks (one per month)
        break;
      case 'max':
        desiredTicks = 10; // Show ~10 ticks for max range
        break;
      default:
        desiredTicks = 10;
    }
    
    return Math.max(1, Math.floor(dataLength / desiredTicks));
  }, [data.length, timeWindow]);

  // Transform price history data into chart format
  const transformData = useMemo(() => {
    return (histories: PriceHistoryPoint[][]): ChartDataPoint[] => {
      if (histories.length === 0) return [];

      // Create a map of timestamp -> prices
      const timestampMap = new Map<number, Record<string, number>>();

      histories.forEach((history, index) => {
        history.forEach((point) => {
          const tokenId = clobTokenIds[index];
          if (!timestampMap.has(point.t)) {
            timestampMap.set(point.t, {});
          }
          timestampMap.get(point.t)![tokenId] = point.p;
        });
      });

      // Convert to array and sort by timestamp
      const chartData: ChartDataPoint[] = Array.from(timestampMap.entries())
        .map(([timestamp, prices]) => ({
          timestamp,
          date: new Date(timestamp * 1000).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          }),
          ...prices,
        }))
        .sort((a, b) => a.timestamp - b.timestamp);

      return chartData;
    };
  }, [clobTokenIds]);

  // Get date input type based on time window
  const getDateInputType = (window: TimeWindow): string => {
    switch (window) {
      case 'hour':
        return 'datetime-local';
      case 'day':
        return 'date';
      case 'week':
        return 'week';
      case 'month':
        return 'month';
      case 'year':
        return 'year';
      case 'max':
        return 'date';
      default:
        return 'date';
    }
  };

  useEffect(() => {
    const loadData = async () => {
      if (clobTokenIds.length === 0) {
        setData([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Fetch all price histories in parallel
        const promises = clobTokenIds.map((tokenId) =>
          fetchPriceHistory(tokenId, interval)
        );
        const responses = await Promise.all(promises);
        const histories = responses.map((res) => res.history);

        // Transform and set data
        const transformedData = transformData(histories);
        setData(transformedData);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to load chart data';
        setError(errorMessage);
        console.error('Error loading chart data:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [clobTokenIds, interval, transformData]);

  if (loading) {
    return (
      <div
        className="flex items-center justify-center border border-border rounded-lg bg-muted/10"
        style={{ height }}
      >
        <div className="flex items-center gap-2 text-muted-foreground">
          <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
          <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
          <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"></span>
          <span className="ml-2">Loading chart data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="flex items-center justify-center border border-border rounded-lg bg-muted/10 text-destructive"
        style={{ height }}
      >
        <div className="text-center">
          <p className="font-medium">Error loading chart</p>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center border border-border rounded-lg bg-muted/10 text-muted-foreground"
        style={{ height }}
      >
        No data available
      </div>
    );
  }

  return (
    <div className="w-full border border-border rounded-lg bg-background p-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <div className="flex items-center gap-2">
          <label htmlFor="time-window" className="text-sm font-medium text-foreground">
            Time Window:
          </label>
          <select
            id="time-window"
            value={timeWindow}
            onChange={(e) => setTimeWindow(e.target.value as TimeWindow)}
            className="px-3 py-1.5 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="hour">Hour</option>
            <option value="day">Day</option>
            <option value="week">Week</option>
            <option value="month">Month</option>
            <option value="year">Year</option>
            <option value="max">Max</option>
          </select>
        </div>
        
        {shouldShowDateInputs && (
          <>
            <div className="flex items-center gap-2">
              <label htmlFor="start-date" className="text-sm font-medium text-foreground">
                Start:
              </label>
              <input
                id="start-date"
                type={getDateInputType(timeWindow)}
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-3 py-1.5 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            
            <div className="flex items-center gap-2">
              <label htmlFor="end-date" className="text-sm font-medium text-foreground">
                End:
              </label>
              <input
                id="end-date"
                type={getDateInputType(timeWindow)}
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-3 py-1.5 text-sm border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 50, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.1} />
          <XAxis
            dataKey="timestamp"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            tickFormatter={formatXAxisTick}
            interval={tickInterval}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            domain={[0, 1]}
            tickFormatter={(value) => value.toFixed(2)}
            width={45}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--background))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
            }}
            labelStyle={{ color: 'hsl(var(--foreground))' }}
            formatter={(value: number) => [
              `${(value * 100).toFixed(2)}%`,
              'Price',
            ]}
          />
          <Legend
            wrapperStyle={{ paddingTop: '10px' }}
            iconType="line"
            formatter={(value) => {
              // Show shortened token ID for legend
              return value.length > 20 ? `${value.substring(0, 20)}...` : value;
            }}
          />
          {clobTokenIds.map((tokenId, index) => (
            <Line
              key={tokenId}
              type="monotone"
              dataKey={tokenId}
              stroke={CHART_COLORS[index % CHART_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              name={`Market ${index + 1}`}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

