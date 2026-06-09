/**
 * Reconnection utility with exponential backoff.
 */

export interface ReconnectOptions {
  maxAttempts: number
  baseDelay: number
  maxDelay: number
  onAttempt?: (attempt: number, delay: number) => void
  onMaxAttemptsReached?: () => void
  onSuccess?: () => void
}

export class ReconnectManager {
  private attempts = 0
  private timer: ReturnType<typeof setTimeout> | null = null
  private options: ReconnectOptions

  constructor(options: Partial<ReconnectOptions> = {}) {
    this.options = {
      maxAttempts: options.maxAttempts ?? 10,
      baseDelay: options.baseDelay ?? 1000,
      maxDelay: options.maxDelay ?? 30000,
      onAttempt: options.onAttempt,
      onMaxAttemptsReached: options.onMaxAttemptsReached,
      onSuccess: options.onSuccess,
    }
  }

  /**
   * Calculate delay with exponential backoff.
   */
  private calculateDelay(): number {
    const delay = this.options.baseDelay * Math.pow(2, this.attempts)
    return Math.min(delay, this.options.maxDelay)
  }

  /**
   * Schedule a reconnection attempt.
   */
  schedule(connectFn: () => void): void {
    if (this.attempts >= this.options.maxAttempts) {
      this.options.onMaxAttemptsReached?.()
      return
    }

    const delay = this.calculateDelay()
    this.attempts++

    this.options.onAttempt?.(this.attempts, delay)

    this.timer = setTimeout(() => {
      connectFn()
    }, delay)
  }

  /**
   * Reset the reconnection state.
   */
  reset(): void {
    this.attempts = 0
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
    this.options.onSuccess?.()
  }

  /**
   * Cancel any pending reconnection.
   */
  cancel(): void {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
  }

  /**
   * Get current attempt count.
   */
  getAttempts(): number {
    return this.attempts
  }

  /**
   * Check if max attempts reached.
   */
  isMaxAttemptsReached(): boolean {
    return this.attempts >= this.options.maxAttempts
  }
}

/**
 * Create a debounced function.
 */
export function debounce<T extends (...args: any[]) => void>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null

  return (...args: Parameters<T>) => {
    if (timer) {
      clearTimeout(timer)
    }
    timer = setTimeout(() => {
      fn(...args)
    }, delay)
  }
}

/**
 * Create a throttled function.
 */
export function throttle<T extends (...args: any[]) => void>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle = false

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args)
      inThrottle = true
      setTimeout(() => {
        inThrottle = false
      }, limit)
    }
  }
}
