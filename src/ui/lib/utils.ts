/**
 * Shared UI utilities.
 */

/**
 * Merge class names, filtering out falsy values.
 * Lightweight replacement for `clsx` + `tailwind-merge`.
 */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}

/** Format a number as a compact currency string. */
export function formatCurrency(value: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value)
}

/** Clamp a value between min and max. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

/** Generate a stable id for list keys. */
export function uid(prefix = 'fc'): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`
}
