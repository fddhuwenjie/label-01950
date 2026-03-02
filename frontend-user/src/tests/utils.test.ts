/**
 * Unit tests for utility functions.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ReconnectManager, debounce, throttle } from '@/utils/reconnect'

describe('ReconnectManager', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('constructor', () => {
    it('should use default options', () => {
      const manager = new ReconnectManager()
      expect(manager.getAttempts()).toBe(0)
      expect(manager.isMaxAttemptsReached()).toBe(false)
    })

    it('should accept custom options', () => {
      const manager = new ReconnectManager({
        maxAttempts: 5,
        baseDelay: 500,
        maxDelay: 10000,
      })
      expect(manager.getAttempts()).toBe(0)
    })
  })

  describe('schedule', () => {
    it('should call connect function after delay', () => {
      const connectFn = vi.fn()
      const manager = new ReconnectManager({ baseDelay: 1000 })

      manager.schedule(connectFn)

      expect(connectFn).not.toHaveBeenCalled()
      vi.advanceTimersByTime(1000)
      expect(connectFn).toHaveBeenCalledTimes(1)
    })

    it('should increment attempts', () => {
      const connectFn = vi.fn()
      const manager = new ReconnectManager({ baseDelay: 1000 })

      manager.schedule(connectFn)
      expect(manager.getAttempts()).toBe(1)

      vi.advanceTimersByTime(1000)
      manager.schedule(connectFn)
      expect(manager.getAttempts()).toBe(2)
    })

    it('should use exponential backoff', () => {
      const connectFn = vi.fn()
      const onAttempt = vi.fn()
      const manager = new ReconnectManager({
        baseDelay: 1000,
        onAttempt,
      })

      // First attempt: 1000ms
      manager.schedule(connectFn)
      expect(onAttempt).toHaveBeenCalledWith(1, 1000)

      vi.advanceTimersByTime(1000)

      // Second attempt: 2000ms
      manager.schedule(connectFn)
      expect(onAttempt).toHaveBeenCalledWith(2, 2000)

      vi.advanceTimersByTime(2000)

      // Third attempt: 4000ms
      manager.schedule(connectFn)
      expect(onAttempt).toHaveBeenCalledWith(3, 4000)
    })

    it('should not exceed max delay', () => {
      const connectFn = vi.fn()
      const onAttempt = vi.fn()
      const manager = new ReconnectManager({
        baseDelay: 1000,
        maxDelay: 5000,
        onAttempt,
      })

      // Schedule multiple times to exceed max delay
      for (let i = 0; i < 5; i++) {
        manager.schedule(connectFn)
        vi.advanceTimersByTime(10000)
      }

      // Check that delay never exceeded maxDelay
      const calls = onAttempt.mock.calls
      calls.forEach((call) => {
        expect(call[1]).toBeLessThanOrEqual(5000)
      })
    })

    it('should stop after max attempts', () => {
      const connectFn = vi.fn()
      const onMaxAttemptsReached = vi.fn()
      const manager = new ReconnectManager({
        maxAttempts: 3,
        baseDelay: 100,
        onMaxAttemptsReached,
      })

      // Schedule 3 times (max)
      for (let i = 0; i < 3; i++) {
        manager.schedule(connectFn)
        vi.advanceTimersByTime(10000)
      }

      // 4th attempt should trigger onMaxAttemptsReached
      manager.schedule(connectFn)
      expect(onMaxAttemptsReached).toHaveBeenCalled()
    })
  })

  describe('reset', () => {
    it('should reset attempts to 0', () => {
      const connectFn = vi.fn()
      const manager = new ReconnectManager({ baseDelay: 1000 })

      manager.schedule(connectFn)
      manager.schedule(connectFn)
      expect(manager.getAttempts()).toBe(2)

      manager.reset()
      expect(manager.getAttempts()).toBe(0)
    })

    it('should cancel pending timer', () => {
      const connectFn = vi.fn()
      const manager = new ReconnectManager({ baseDelay: 1000 })

      manager.schedule(connectFn)
      manager.reset()

      vi.advanceTimersByTime(2000)
      expect(connectFn).not.toHaveBeenCalled()
    })

    it('should call onSuccess callback', () => {
      const onSuccess = vi.fn()
      const manager = new ReconnectManager({ onSuccess })

      manager.reset()
      expect(onSuccess).toHaveBeenCalled()
    })
  })

  describe('cancel', () => {
    it('should cancel pending timer', () => {
      const connectFn = vi.fn()
      const manager = new ReconnectManager({ baseDelay: 1000 })

      manager.schedule(connectFn)
      manager.cancel()

      vi.advanceTimersByTime(2000)
      expect(connectFn).not.toHaveBeenCalled()
    })

    it('should not reset attempts', () => {
      const connectFn = vi.fn()
      const manager = new ReconnectManager({ baseDelay: 1000 })

      manager.schedule(connectFn)
      manager.cancel()

      expect(manager.getAttempts()).toBe(1)
    })
  })

  describe('isMaxAttemptsReached', () => {
    it('should return false when under max', () => {
      const manager = new ReconnectManager({ maxAttempts: 5 })
      expect(manager.isMaxAttemptsReached()).toBe(false)
    })

    it('should return true when at max', () => {
      const connectFn = vi.fn()
      const manager = new ReconnectManager({ maxAttempts: 2, baseDelay: 100 })

      manager.schedule(connectFn)
      vi.advanceTimersByTime(1000)
      manager.schedule(connectFn)
      vi.advanceTimersByTime(1000)

      expect(manager.isMaxAttemptsReached()).toBe(true)
    })
  })
})

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should delay function execution', () => {
    const fn = vi.fn()
    const debouncedFn = debounce(fn, 300)

    debouncedFn()
    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(300)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('should reset timer on subsequent calls', () => {
    const fn = vi.fn()
    const debouncedFn = debounce(fn, 300)

    debouncedFn()
    vi.advanceTimersByTime(200)
    debouncedFn()
    vi.advanceTimersByTime(200)
    debouncedFn()
    vi.advanceTimersByTime(200)

    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('should pass arguments to function', () => {
    const fn = vi.fn()
    const debouncedFn = debounce(fn, 300)

    debouncedFn('arg1', 'arg2')
    vi.advanceTimersByTime(300)

    expect(fn).toHaveBeenCalledWith('arg1', 'arg2')
  })

  it('should only call once for rapid calls', () => {
    const fn = vi.fn()
    const debouncedFn = debounce(fn, 300)

    for (let i = 0; i < 10; i++) {
      debouncedFn()
    }

    vi.advanceTimersByTime(300)
    expect(fn).toHaveBeenCalledTimes(1)
  })
})

describe('throttle', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should execute immediately on first call', () => {
    const fn = vi.fn()
    const throttledFn = throttle(fn, 300)

    throttledFn()
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('should ignore calls within throttle period', () => {
    const fn = vi.fn()
    const throttledFn = throttle(fn, 300)

    throttledFn()
    throttledFn()
    throttledFn()

    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('should allow calls after throttle period', () => {
    const fn = vi.fn()
    const throttledFn = throttle(fn, 300)

    throttledFn()
    expect(fn).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(300)
    throttledFn()
    expect(fn).toHaveBeenCalledTimes(2)
  })

  it('should pass arguments to function', () => {
    const fn = vi.fn()
    const throttledFn = throttle(fn, 300)

    throttledFn('arg1', 'arg2')
    expect(fn).toHaveBeenCalledWith('arg1', 'arg2')
  })
})
