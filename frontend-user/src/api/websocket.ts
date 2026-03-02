/**
 * WebSocket client for LSP communication with reconnection support.
 */

export interface LSPMessage {
  jsonrpc: string
  id?: number | string
  method?: string
  params?: Record<string, unknown>
  result?: unknown
  error?: {
    code: number
    message: string
    data?: unknown
  }
}

export interface Position {
  line: number
  character: number
}

export interface Range {
  start: Position
  end: Position
}

export interface Diagnostic {
  range: Range
  severity: number
  code?: string
  source: string
  message: string
}

export interface CompletionItem {
  label: string
  kind: number
  detail?: string
  documentation?: string
  insertText?: string
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

export interface WebSocketClientOptions {
  url: string
  reconnectAttempts?: number
  reconnectInterval?: number
  onMessage?: (message: LSPMessage) => void
  onStatusChange?: (status: ConnectionStatus) => void
  onDiagnostics?: (uri: string, diagnostics: Diagnostic[]) => void
  onCompletion?: (items: CompletionItem[]) => void
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts: number
  private reconnectInterval: number
  private currentAttempt = 0
  private messageId = 0
  private pendingRequests: Map<number, {
    resolve: (value: unknown) => void
    reject: (reason: unknown) => void
  }> = new Map()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private status: ConnectionStatus = 'disconnected'

  private onMessage?: (message: LSPMessage) => void
  private onStatusChange?: (status: ConnectionStatus) => void
  private onDiagnostics?: (uri: string, diagnostics: Diagnostic[]) => void
  private onCompletion?: (items: CompletionItem[]) => void

  constructor(options: WebSocketClientOptions) {
    this.url = options.url
    this.reconnectAttempts = options.reconnectAttempts ?? 10
    this.reconnectInterval = options.reconnectInterval ?? 1000
    this.onMessage = options.onMessage
    this.onStatusChange = options.onStatusChange
    this.onDiagnostics = options.onDiagnostics
    this.onCompletion = options.onCompletion
  }

  private setStatus(status: ConnectionStatus): void {
    this.status = status
    this.onStatusChange?.(status)
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    this.setStatus('connecting')

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected')
        this.currentAttempt = 0
        this.setStatus('connected')
      }

      this.ws.onmessage = (event) => {
        this.handleMessage(event.data)
      }

      this.ws.onclose = (event) => {
        console.log('[WebSocket] Closed:', event.code, event.reason)
        this.setStatus('disconnected')
        this.attemptReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
      }
    } catch (error) {
      console.error('[WebSocket] Connection error:', error)
      this.setStatus('disconnected')
      this.attemptReconnect()
    }
  }

  private attemptReconnect(): void {
    if (this.currentAttempt >= this.reconnectAttempts) {
      console.log('[WebSocket] Max reconnection attempts reached')
      return
    }

    // Exponential backoff
    const delay = this.reconnectInterval * Math.pow(2, this.currentAttempt)
    this.currentAttempt++

    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.currentAttempt}/${this.reconnectAttempts})`)

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, delay)
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.setStatus('disconnected')
  }

  private handleMessage(data: string): void {
    try {
      const message: LSPMessage = JSON.parse(data)
      this.onMessage?.(message)

      // Handle response to pending request
      if (message.id !== undefined && this.pendingRequests.has(message.id as number)) {
        const pending = this.pendingRequests.get(message.id as number)!
        this.pendingRequests.delete(message.id as number)

        if (message.error) {
          pending.reject(message.error)
        } else {
          pending.resolve(message.result)
        }
        return
      }

      // Handle notifications
      if (message.method === 'textDocument/publishDiagnostics') {
        const params = message.params as { uri: string; diagnostics: Diagnostic[] }
        this.onDiagnostics?.(params.uri, params.diagnostics)
      }

      // Handle completion response in result
      if (message.result && typeof message.result === 'object' && 'items' in (message.result as object)) {
        const result = message.result as { items: CompletionItem[] }
        this.onCompletion?.(result.items)
      }

      // Handle diagnostics in result
      if (message.result && typeof message.result === 'object' && 'diagnostics' in (message.result as object)) {
        const result = message.result as { uri: string; diagnostics: Diagnostic[] }
        this.onDiagnostics?.(result.uri, result.diagnostics)
      }
    } catch (error) {
      console.error('[WebSocket] Failed to parse message:', error)
    }
  }

  private send(message: LSPMessage): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Cannot send message, not connected')
      return
    }

    this.ws.send(JSON.stringify(message))
  }

  private sendRequest(method: string, params: Record<string, unknown>): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const id = ++this.messageId

      this.pendingRequests.set(id, { resolve, reject })

      this.send({
        jsonrpc: '2.0',
        id,
        method,
        params,
      })

      // Timeout after 5 seconds
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id)
          reject(new Error('Request timeout'))
        }
      }, 5000)
    })
  }

  // LSP Methods

  async didOpen(uri: string, text: string, languageId = 'sql'): Promise<void> {
    await this.sendRequest('textDocument/didOpen', {
      textDocument: {
        uri,
        languageId,
        version: 1,
        text,
      },
    })
  }

  async didChange(uri: string, text: string): Promise<void> {
    await this.sendRequest('textDocument/didChange', {
      textDocument: { uri },
      contentChanges: [{ text }],
    })
  }

  async didClose(uri: string): Promise<void> {
    this.send({
      jsonrpc: '2.0',
      method: 'textDocument/didClose',
      params: {
        textDocument: { uri },
      },
    })
  }

  async requestCompletion(uri: string, position: Position): Promise<CompletionItem[]> {
    const result = await this.sendRequest('textDocument/completion', {
      textDocument: { uri },
      position,
    }) as { items: CompletionItem[] }

    return result.items || []
  }

  async setDialect(uri: string, dialect: string): Promise<void> {
    await this.sendRequest('setDialect', {
      uri,
      dialect,
    })
  }

  getStatus(): ConnectionStatus {
    return this.status
  }

  isConnected(): boolean {
    return this.status === 'connected'
  }
}

// Create singleton instance
let wsClient: WebSocketClient | null = null

export function getWebSocketClient(): WebSocketClient {
  if (!wsClient) {
    const wsUrl = import.meta.env.PROD
      ? `ws://${window.location.host}/ws`
      : 'ws://localhost:8000/ws'

    wsClient = new WebSocketClient({
      url: wsUrl,
    })
  }
  return wsClient
}

export function createWebSocketClient(options: WebSocketClientOptions): WebSocketClient {
  return new WebSocketClient(options)
}
