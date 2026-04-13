import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Normalize and format a percentage value
 * Handles: numbers (0-1 or 0-100), strings, arrays, objects
 * Returns formatted string like "62.5%"
 */
export function formatPercentage(value: any): string {
  let numValue: number;

  // Handle arrays (extract first element if it's an array)
  if (Array.isArray(value)) {
    if (value.length === 0) return "0%";
    numValue = parseFloat(String(value[0]));
  }
  // Handle objects with value property
  else if (typeof value === "object" && value !== null && "value" in value) {
    numValue = parseFloat(String(value.value));
  }
  // Handle strings
  else if (typeof value === "string") {
    numValue = parseFloat(value);
  }
  // Handle numbers
  else if (typeof value === "number") {
    numValue = value;
  }
  // Handle null/undefined
  else {
    return "0%";
  }

  // Validate the parsed number
  if (isNaN(numValue)) return "0%";

  // Normalize: if value <= 1, assume it's a decimal (0.0-1.0) and convert to percentage
  // if value > 1, assume it's already a percentage (0-100)
  let percentage: number;
  if (numValue <= 1 && numValue >= 0) {
    percentage = numValue * 100;
  } else if (numValue > 1 && numValue <= 100) {
    percentage = numValue;
  } else if (numValue > 100) {
    // Clamp to 100 if somehow over 100
    percentage = 100;
  } else {
    // Negative or very large, clamp to 0
    percentage = Math.max(0, Math.min(100, numValue));
  }

  // Clamp to 0-100 range
  percentage = Math.max(0, Math.min(100, percentage));

  // Format to 1 decimal place
  return `${percentage.toFixed(1)}%`;
}

/**
 * Normalize a percentage value for progress bar width
 * Returns a number between 0-100
 */
export function normalizeProgressValue(value: any): number {
  let numValue: number;

  // Handle arrays
  if (Array.isArray(value)) {
    if (value.length === 0) return 0;
    numValue = parseFloat(String(value[0]));
  }
  // Handle objects
  else if (typeof value === "object" && value !== null && "value" in value) {
    numValue = parseFloat(String(value.value));
  }
  // Handle strings
  else if (typeof value === "string") {
    numValue = parseFloat(value);
  }
  // Handle numbers
  else if (typeof value === "number") {
    numValue = value;
  }
  // Handle null/undefined
  else {
    return 0;
  }

  // Validate
  if (isNaN(numValue)) return 0;

  // Normalize
  let percentage: number;
  if (numValue <= 1 && numValue >= 0) {
    percentage = numValue * 100;
  } else if (numValue > 1 && numValue <= 100) {
    percentage = numValue;
  } else if (numValue > 100) {
    percentage = 100;
  } else {
    percentage = Math.max(0, Math.min(100, numValue));
  }

  // Clamp to 0-100
  return Math.max(0, Math.min(100, percentage));
}
