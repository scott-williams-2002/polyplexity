import { PriceHistoryResponse } from '../types';

export async function fetchPriceHistory(clobTokenId: string, interval: string = 'all', fidelity: number = 720): Promise<PriceHistoryResponse> {
  try {
    const url = new URL('https://clob.polymarket.com/prices-history');
    url.searchParams.set('market', clobTokenId);
    url.searchParams.set('interval', interval);
    url.searchParams.set('fidelity', fidelity.toString());
    
    const response = await fetch(url.toString());
    
    if (!response.ok) {
      throw new Error(`Failed to fetch price history: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching price history:', error);
    throw error;
  }
}
