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