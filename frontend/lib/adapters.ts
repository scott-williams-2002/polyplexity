/**
 * Adapter layer to convert between frontend API types and Vite app types
 */
import { ExecutionTraceEvent, Source, ReferenceSource, ApiMessage, Message, ApprovedMarket } from "../types";
import { generateId, generateStableId } from "./utils";

/**
 * Convert execution trace events to a formatted reasoning string.
 * Handles both envelope format (from streaming) and direct format (from refresh).
 */
export function executionTraceToReasoning(events: ExecutionTraceEvent[]): string {
  if (!events || events.length === 0) {
    return "";
  }

  const reasoningParts: string[] = [];

  for (const event of events) {
    // Extract data - handle both formats
    // Direct format: event.data exists directly
    // Envelope format: event.data.payload.data (already normalized in useChatStream)
    const eventData = event.data || {};

    // Handle reasoning type events - these have reasoning directly in data
    if (event.type === "reasoning" && eventData.reasoning) {
      reasoningParts.push(`> ${eventData.reasoning}`);
    } 
    // Handle node_call events
    else if (event.type === "node_call") {
      // Node calls don't typically add to reasoning, but we can add a note if needed
      if (eventData.event) {
        // Skip generic node_call events, only show if there's additional context
      }
    }
    // Handle custom events with reasoning
    else if (event.type === "custom" && eventData) {
      // Check for reasoning in custom events (supervisor_decision, etc.)
      if (eventData.reasoning) {
        reasoningParts.push(`> ${eventData.reasoning}`);
      } 
      // Handle supervisor_decision events
      else if (eventData.event === "supervisor_decision") {
        if (eventData.reasoning) {
          reasoningParts.push(`> ${eventData.reasoning}`);
        } else if (eventData.topic) {
          reasoningParts.push(`> Analyzing: ${eventData.topic}`);
        }
      } 
      // Handle other custom events
      else if (eventData.event === "generated_queries" && eventData.queries) {
        reasoningParts.push(`> Generated ${eventData.queries.length} search queries`);
      } else if (eventData.event === "search_start" && eventData.query) {
        reasoningParts.push(`> Searching: ${eventData.query}`);
      } else if (eventData.event === "web_search_url" && eventData.markdown) {
        // Preserve markdown link format in reasoning so it can be parsed later
        reasoningParts.push(`> Found source: ${eventData.markdown}`);
      } else if (eventData.event === "research_synthesis_done") {
        reasoningParts.push(`> Synthesizing research results...`);
      } else if (eventData.event === "writing_report") {
        reasoningParts.push(`> Writing final report...`);
      } else if (eventData.event === "market_research_start") {
        reasoningParts.push(`> Starting market research...`);
      } else if (eventData.event === "tag_selected" && eventData.tags) {
        const tagCount = Array.isArray(eventData.tags) ? eventData.tags.length : 0;
        reasoningParts.push(`> Selected ${tagCount} relevant market tags`);
      } else if (eventData.event === "market_approved") {
        const question = eventData.question || "";
        if (question) {
          const shortQuestion = question.length > 60 ? question.substring(0, 60) + "..." : question;
          reasoningParts.push(`> Found market: ${shortQuestion}`);
        } else {
          reasoningParts.push(`> Approved market found`);
        }
      } else if (eventData.event === "market_research_complete") {
        const reasoning = eventData.reasoning || "";
        if (reasoning) {
          reasoningParts.push(`> Market research complete: ${reasoning.substring(0, 200)}${reasoning.length > 200 ? "..." : ""}`);
        } else {
          reasoningParts.push(`> Market research complete`);
        }
      } else if (eventData.event === "polymarket_blurb_generated") {
        reasoningParts.push(`> Generated market recommendations`);
      }
    }
    // Handle search type events
    else if (event.type === "search" && eventData.query) {
      reasoningParts.push(`> Searching: ${eventData.query}`);
    }
    // Handle state_update events
    else if (event.type === "state_update") {
      // Skip polymarket data from reasoning display (but keep in trace for persistence)
      if (event.node === "call_market_research" && eventData.approved_markets) {
        // Don't add to reasoning - approved_markets are displayed in charts
        continue;
      }
      if (event.node === "rewrite_polymarket_response" && eventData.polymarket_blurb) {
        // Don't add to reasoning - polymarket_blurb is displayed separately
        continue;
      }
      // State updates typically don't add to reasoning trace
      // But we can add notes for specific state changes if needed
      if (eventData.event === "research_notes_added") {
        // Don't add to reasoning - research notes are in the final report
      }
    }
  }

  const result = reasoningParts.join("\n\n");
  console.log('[adapters] executionTraceToReasoning - input events:', events.length, 'output length:', result.length);
  return result;
}

/**
 * Convert Source to ReferenceSource format
 */
export function sourceToReferenceSource(source: Source): ReferenceSource {
  // Extract domain from URL
  let domain = "";
  try {
    const url = new URL(source.url);
    domain = url.hostname.replace(/^www\./, "");
  } catch {
    // If URL parsing fails, try to extract from markdown
    const match = source.markdown.match(/^\[.*?\]\(https?:\/\/([^\/]+)/);
    if (match) {
      domain = match[1].replace(/^www\./, "");
    }
  }

  // Extract title from markdown link text
  let title = domain;
  const titleMatch = source.markdown.match(/^\[(.*?)\]/);
  if (titleMatch) {
    title = titleMatch[1];
  }

  // Use stable ID based on URL to prevent re-renders when same source is processed again
  const stableId = generateStableId(source.url);

  return {
    id: stableId,
    title,
    url: source.url,
    domain,
  };
}

/**
 * Parse markdown links from reasoning text and convert to ReferenceSource array
 */
export function parseMarkdownLinks(reasoning: string): ReferenceSource[] {
  if (!reasoning) return [];
  
  const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
  const links: ReferenceSource[] = [];
  const seenUrls = new Set<string>();
  
  let match;
  while ((match = markdownLinkRegex.exec(reasoning)) !== null) {
    const [, linkText, url] = match;
    
    // Skip if URL already seen (deduplicate)
    if (seenUrls.has(url)) continue;
    seenUrls.add(url);
    
    // Extract domain from URL
    let domain = "";
    try {
      const urlObj = new URL(url);
      domain = urlObj.hostname.replace(/^www\./, "");
    } catch {
      // If URL parsing fails, try to extract from the URL string
      const domainMatch = url.match(/https?:\/\/(?:www\.)?([^\/]+)/);
      if (domainMatch) {
        domain = domainMatch[1];
      } else {
        domain = url; // Fallback to full URL
      }
    }
    
    links.push({
      id: generateStableId(url), // Use stable ID based on URL
      title: linkText.trim() || domain,
      url: url,
      domain: domain,
    });
  }
  
  return links;
}

/**
 * Extract approved markets from execution trace
 */
export function extractApprovedMarketsFromTrace(events: ExecutionTraceEvent[]): ApprovedMarket[] {
  if (!events || events.length === 0) return [];
  
  let latestMarkets: ApprovedMarket[] = [];
  
  for (const event of events) {
    if (event.type === "state_update" && event.node === "call_market_research") {
      const approvedMarkets = event.data?.approved_markets;
      if (Array.isArray(approvedMarkets) && approvedMarkets.length > 0) {
        latestMarkets = approvedMarkets;
      }
    }
  }
  
  return latestMarkets;
}

/**
 * Extract polymarket blurb from execution trace
 */
export function extractPolymarketBlurbFromTrace(events: ExecutionTraceEvent[]): string | undefined {
  if (!events || events.length === 0) return undefined;
  
  let latestBlurb: string | undefined;
  
  for (const event of events) {
    if (event.type === "state_update" && event.node === "rewrite_polymarket_response") {
      const blurb = event.data?.polymarket_blurb;
      if (typeof blurb === "string" && blurb.length > 0) {
        latestBlurb = blurb;
      }
    }
  }
  
  return latestBlurb;
}

/**
 * Extract search result links from execution trace
 */
export function extractSearchLinksFromTrace(events: ExecutionTraceEvent[]): ReferenceSource[] {
  if (!events || events.length === 0) return [];
  
  const links: ReferenceSource[] = [];
  const seenUrls = new Set<string>();
  
  for (const event of events) {
    let results: Array<{title?: string; url?: string}> | undefined;
    
    // Handle search type events
    if (event.type === "search" && event.data?.results) {
      results = event.data.results;
    }
    // Handle custom events with search results
    else if (event.type === "custom" && event.data?.event === "search" && event.data?.results) {
      results = event.data.results;
    }
    // Handle trace events that were normalized (check data.results)
    else if (event.data?.results && Array.isArray(event.data.results)) {
      results = event.data.results;
    }
    
    if (results && Array.isArray(results)) {
      for (const result of results) {
        if (result.url && !seenUrls.has(result.url)) {
          seenUrls.add(result.url);
          const title = result.title || result.url;
          const markdown = `[${title}](${result.url})`;
          const source: Source = { url: result.url, markdown };
          links.push(sourceToReferenceSource(source));
        }
      }
    }
  }
  
  return links;
}

/**
 * Convert API message format to Vite Message format
 */
export function apiMessageToViteMessage(msg: ApiMessage, id?: string): Message {
  const reasoning = msg.execution_trace
    ? executionTraceToReasoning(msg.execution_trace)
    : "";

  // Parse markdown links from reasoning to populate sources
  const parsedSources = parseMarkdownLinks(reasoning);
  
  // Extract search result links from execution trace
  const searchLinks = msg.execution_trace
    ? extractSearchLinksFromTrace(msg.execution_trace)
    : [];
  
  // Merge and deduplicate sources by URL
  const allSources: ReferenceSource[] = [];
  const seenUrls = new Set<string>();
  
  for (const source of [...parsedSources, ...searchLinks]) {
    if (!seenUrls.has(source.url)) {
      seenUrls.add(source.url);
      allSources.push(source);
    }
  }
  
  // Extract approved markets and polymarket blurb from execution trace
  const approvedMarkets = msg.execution_trace
    ? extractApprovedMarketsFromTrace(msg.execution_trace)
    : undefined;
  
  const polymarketBlurb = msg.execution_trace
    ? extractPolymarketBlurbFromTrace(msg.execution_trace)
    : undefined;

  return {
    id: id || generateId(),
    role: msg.role,
    content: msg.content,
    reasoning: reasoning || undefined,
    sources: allSources.length > 0 ? allSources : undefined,
    approvedMarkets: approvedMarkets && approvedMarkets.length > 0 ? approvedMarkets : undefined,
    polymarketBlurb: polymarketBlurb,
    timestamp: msg.timestamp ? new Date(msg.timestamp).getTime() : Date.now(),
    stage: "completed",
    isStreaming: false,
  };
}

