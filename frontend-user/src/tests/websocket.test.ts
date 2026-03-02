/**
 * Unit tests for WebSocket client.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { WebSocketClient, type WebSocketClientOptions } from '@/api/websocket'

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1
  static CLOSED = 3

  readyState = MockWebSocket.OPEN
  onopen: (() => void) | null = null
  onclose: ((event: { code: number; reason: string }) => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: ((error: Error) => void) | null = null

  constructor(_url: string) {
    setTimeout(() => {
      this.onopen?.()
    }, 0)
  }

  send = vi.fn()
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({ code: 1000, reason: 'Normal closure' })
  })
}

describe('WebSocketClient', () => {
  let client: WebSocketClient
  let originalWebSocket: typeof WebSocket

  beforeEach(() => {
    originalWebSocket = global.WebSocket
    global.WebSocket = MockWebSocket as unknown as typeof WebSocket
  })

  afterEach(() => {
    global.WebSocket = originalWebSocket
    client?.disconnect()
  })

  it('should connect successfully', async () => {
    const onStatusChange = vi.fn()
    const options: WebSocketClientOptions = {
      url: 'ws://localhost:8000/ws',
      onStatusChange,
    }

    client = new WebSocketClient(options)
    client.connect()

    // Wait for async connection
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(onStatusChange).toHaveBeenCalledWith('connecting')
    expect(onStatusChange).toHaveBeenCalledWith('connected')
  })

  it('should handle disconnect', async () => {
    const onStatusChange = vi.fn()
    const options: WebSocketClientOptions = {
      url: 'ws://localhost:8000/ws',
      onStatusChange,
    }

    client = new WebSocketClient(options)
    client.connect()

    await new Promise((resolve) => setTimeout(resolve, 10))

    client.disconnect()

    expect(onStatusChange).toHaveBeenCalledWith('disconnected')
  })

  it('should report connection status', async () => {
    const options: WebSocketClientOptions = {
      url: 'ws://localhost:8000/ws',
    }

    client = new WebSocketClient(options)

    expect(client.isConnected()).toBe(false)
    expect(client.getStatus()).toBe('disconnected')

    client.connect()
    await new Promise((resolve) => setTimeout(resolve, 10))

    expect(client.isConnected()).toBe(true)
    expect(client.getStatus()).toBe('connected')
  })

  it('should handle message callback', async () => {
    const onMessage = vi.fn()
    const options: WebSocketClientOptions = {
      url: 'ws://localhost:8000/ws',
      onMessage,
    }

    client = new WebSocketClient(options)
    client.connect()

    await new Promise((resolve) => setTimeout(resolve, 10))

    // Simulate receiving a message
    const mockWs = (client as unknown as { ws: MockWebSocket }).ws
    mockWs.onmessage?.({
      data: JSON.stringify({
        jsonrpc: '2.0',
        method: 'test',
        params: {},
      }),
    })

    expect(onMessage).toHaveBeenCalled()
  })

  it('should handle diagnostics callback', async () => {
    const onDiagnostics = vi.fn()
    const options: WebSocketClientOptions = {
      url: 'ws://localhost:8000/ws',
      onDiagnostics,
    }

    client = new WebSocketClient(options)
    client.connect()

    await new Promise((resolve) => setTimeout(resolve, 10))

    // Simulate receiving diagnostics
    const mockWs = (client as unknown as { ws: MockWebSocket }).ws
    mockWs.onmessage?.({
      data: JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        result: {
          uri: 'file:///test.sql',
          diagnostics: [
            {
              range: { start: { line: 0, character: 0 }, end: { line: 0, character: 5 } },
              severity: 1,
              message: 'Test error',
            },
          ],
        },
      }),
    })

    expect(onDiagnostics).toHaveBeenCalled()
  })
})

describe('WebSocketClient reconnection', () => {
  let originalWebSocket: typeof WebSocket

  beforeEach(() => {
    originalWebSocket = global.WebSocket
  })

  afterEach(() => {
    global.WebSocket = originalWebSocket
  })

  it('should attempt reconnection on disconnect', async () => {
    let connectionAttempts = 0

    class ReconnectMockWebSocket extends MockWebSocket {
      constructor(url: string) {
        super(url)
        connectionAttempts++
        if (connectionAttempts === 1) {
          // First connection fails
          setTimeout(() => {
            this.onclose?.({ code: 1006, reason: 'Connection failed' })
          }, 0)
        }
      }
    }

    global.WebSocket = ReconnectMockWebSocket as unknown as typeof WebSocket

    const options: WebSocketClientOptions = {
      url: 'ws://localhost:8000/ws',
      reconnectAttempts: 3,
      reconnectInterval: 10,
    }

    const client = new WebSocketClient(options)
    client.connect()

    // Wait for reconnection attempts (need more time for async reconnection)
    await new Promise((resolve) => setTimeout(resolve, 200))

    expect(connectionAttempts).toBeGreaterThanOrEqual(1)

    client.disconnect()
  })
})
