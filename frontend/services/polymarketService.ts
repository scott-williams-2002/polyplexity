import { PriceHistoryResponse } from '../types';

/**
 * Fetch price history with specific interval and fidelity parameters
 */
async function fetchWithParams(
  clobTokenId: string,
  interval: string,
  fidelity?: number
): Promise<PriceHistoryResponse> {
  const url = new URL('https://clob.polymarket.com/prices-history');
  url.searchParams.set('market', clobTokenId);
  url.searchParams.set('interval', interval);
  if (fidelity !== undefined) {
    url.searchParams.set('fidelity', fidelity.toString());
  }
  
  const response = await fetch(url.toString());
  
  if (!response.ok) {
    throw new Error(`Failed to fetch price history: ${response.statusText}`);
  }
  
  return await response.json();
}

/**
 * Fetch price history for a Polymarket market with automatic retry logic.
 * Tries max (no fidelity) first, then all with fidelity=60 if the first returns empty data.
 */
export async function fetchPriceHistory(clobTokenId: string): Promise<PriceHistoryResponse> {
  // First attempt: max with no fidelity
  try {
    console.log('[fetchPriceHistory] Attempting: interval=max, no fidelity');
    const result = await fetchWithParams(clobTokenId, 'max');
    
    // Check if we have data
    if (result.history && Array.isArray(result.history) && result.history.length > 0) {
      console.log(`[fetchPriceHistory] Success with interval=max, no fidelity (${result.history.length} points)`);
      return result;
    }
    
    console.log('[fetchPriceHistory] No data returned for interval=max, no fidelity');
  } catch (error) {
    console.error(`[fetchPriceHistory] Error fetching with interval=max, no fidelity: ${error instanceof Error ? error.message : String(error)}`);
  }

  // Second attempt: all with fidelity=60
  try {
    console.log('[fetchPriceHistory] Attempting: interval=all, fidelity=60');
    const result = await fetchWithParams(clobTokenId, 'all', 60);
    
    // Check if we have data
    if (result.history && Array.isArray(result.history) && result.history.length > 0) {
      console.log(`[fetchPriceHistory] Success with interval=all, fidelity=60 (${result.history.length} points)`);
      return result;
    }
    
    console.log('[fetchPriceHistory] No data returned for interval=all, fidelity=60');
  } catch (error) {
    console.error(`[fetchPriceHistory] Error fetching with interval=all, fidelity=60: ${error instanceof Error ? error.message : String(error)}`);
  }

  // Both attempts failed
  throw new Error('Failed to fetch price history: both attempts (max with no fidelity, and all with fidelity=60) returned empty data or failed');
}
