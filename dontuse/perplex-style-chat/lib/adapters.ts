/**
 * Adapter layer to convert between frontend API types and Vite app types
 */
import { ExecutionTraceEvent, Source, ReferenceSource, ApiMessage, Message } from "../types";
import { generateId } from "./utils";

/**
 * Convert execution trace events to a formatted reasoning string
 */
export function executionTraceToReasoning(events: ExecutionTraceEvent[]): string {
  if (!events || events.length === 0) {
    return "";
  }

  const reasoningParts: string[] = [];

  for (const event of events) {
    // Handle reasoning type events - these have reasoning directly in data
    if (event.type === "reasoning" && event.data && event.data.reasoning) {
      reasoningParts.push(`> ${event.data.reasoning}`);
    } 
    // Handle custom events with reasoning
    else if (event.type === "custom" && event.data) {
      // Check for reasoning in custom events (supervisor_decision, etc.)
      if (event.data.reasoning) {
        reasoningParts.push(`> ${event.data.reasoning}`);
      } 
      // Handle supervisor_decision events
      else if (event.data.event === "supervisor_decision") {
        if (event.data.reasoning) {
          reasoningParts.push(`> ${event.data.reasoning}`);
        } else if (event.data.topic) {
          reasoningParts.push(`> Analyzing: ${event.data.topic}`);
        }
      } 
      // Handle other custom events
      else if (event.data.event === "generated_queries" && event.data.queries) {
        reasoningParts.push(`> Generated ${event.data.queries.length} search queries`);
      } else if (event.data.event === "search_start" && event.data.query) {
        reasoningParts.push(`> Searching: ${event.data.query}`);
      } else if (event.data.event === "web_search_url" && event.data.markdown) {
        // Preserve markdown link format in reasoning so it can be parsed later
        reasoningParts.push(`> Found source: ${event.data.markdown}`);
      } else if (event.data.event === "research_synthesis_done") {
        reasoningParts.push(`> Synthesizing research results...`);
      } else if (event.data.event === "writing_report") {
        reasoningParts.push(`> Writing final report...`);
      }
    }
    // Handle search type events
    else if (event.type === "search" && event.data && event.data.query) {
      reasoningParts.push(`> Searching: ${event.data.query}`);
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

  return {
    id: generateId(),
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
      id: generateId(),
      title: linkText.trim() || domain,
      url: url,
      domain: domain,
    });
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

  return {
    id: id || generateId(),
    role: msg.role,
    content: msg.content,
    reasoning: reasoning || undefined,
    sources: parsedSources, // Sources parsed from reasoning markdown links
    timestamp: msg.timestamp ? new Date(msg.timestamp).getTime() : Date.now(),
    stage: "completed",
    isStreaming: false,
  };
}

