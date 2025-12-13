/**
 * API key management utilities
 * Handles storing and retrieving API key from localStorage
 */

const STORAGE_KEY = 'polyplexity_api_key';

/**
 * Retrieve API key from localStorage
 */
export function getApiKey(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch (error) {
    console.error('Error retrieving API key from localStorage:', error);
    return null;
  }
}

/**
 * Save API key to localStorage
 */
export function setApiKey(key: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, key);
  } catch (error) {
    console.error('Error saving API key to localStorage:', error);
    throw error;
  }
}

/**
 * Remove API key from localStorage
 */
export function clearApiKey(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Error clearing API key from localStorage:', error);
  }
}

/**
 * Check if API key exists in localStorage
 */
export function hasApiKey(): boolean {
  const key = getApiKey();
  return key !== null && key.trim() !== '';
}

