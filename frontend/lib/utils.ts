import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Helper to delay execution (for mocking streaming)
export const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

/**
 * Generate a deterministic ID from a string (e.g., URL)
 * Uses a simple hash function to create stable IDs
 */
export function generateStableId(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  // Convert to base36 and ensure positive
  return Math.abs(hash).toString(36).substring(0, 9);
}