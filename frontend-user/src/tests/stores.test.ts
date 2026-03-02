/**
 * Unit tests for Pinia stores.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEditorStore } from '@/stores/editor'
import { useConnectionStore } from '@/stores/connection'
import type { Diagnostic } from '@/api/websocket'

describe('EditorStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('should have empty content initially', () => {
      const store = useEditorStore()
      expect(store.content).toBe('')
    })

    it('should have ansi dialect by default', () => {
      const store = useEditorStore()
      expect(store.dialect).toBe('ansi')
    })

    it('should have empty diagnostics initially', () => {
      const store = useEditorStore()
      expect(store.diagnostics).toEqual([])
    })

    it('should have cursor at line 1, column 1 initially', () => {
      const store = useEditorStore()
      expect(store.cursorPosition).toEqual({ line: 1, column: 1 })
    })

    it('should not be linting initially', () => {
      const store = useEditorStore()
      expect(store.isLinting).toBe(false)
    })
  })

  describe('setContent', () => {
    it('should update content', () => {
      const store = useEditorStore()
      store.setContent('SELECT * FROM users')
      expect(store.content).toBe('SELECT * FROM users')
    })

    it('should handle empty content', () => {
      const store = useEditorStore()
      store.setContent('some content')
      store.setContent('')
      expect(store.content).toBe('')
    })
  })

  describe('setDialect', () => {
    it('should update dialect', () => {
      const store = useEditorStore()
      store.setDialect('sparksql')
      expect(store.dialect).toBe('sparksql')
    })

    it('should accept hive dialect', () => {
      const store = useEditorStore()
      store.setDialect('hive')
      expect(store.dialect).toBe('hive')
    })
  })

  describe('setDiagnostics', () => {
    it('should update diagnostics', () => {
      const store = useEditorStore()
      const diagnostics: Diagnostic[] = [
        {
          range: {
            start: { line: 0, character: 0 },
            end: { line: 0, character: 5 }
          },
          severity: 1,
          message: 'Test error',
          source: 'sqlfluff'
        }
      ]
      store.setDiagnostics(diagnostics)
      expect(store.diagnostics).toEqual(diagnostics)
    })

    it('should set isLinting to false', () => {
      const store = useEditorStore()
      store.setLinting(true)
      store.setDiagnostics([])
      expect(store.isLinting).toBe(false)
    })
  })

  describe('computed properties', () => {
    it('should count errors correctly', () => {
      const store = useEditorStore()
      store.setDiagnostics([
        { range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, severity: 1, message: 'Error 1', source: 'test' },
        { range: { start: { line: 1, character: 0 }, end: { line: 1, character: 1 } }, severity: 1, message: 'Error 2', source: 'test' },
        { range: { start: { line: 2, character: 0 }, end: { line: 2, character: 1 } }, severity: 2, message: 'Warning', source: 'test' },
      ])
      expect(store.errorCount).toBe(2)
    })

    it('should count warnings correctly', () => {
      const store = useEditorStore()
      store.setDiagnostics([
        { range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, severity: 1, message: 'Error', source: 'test' },
        { range: { start: { line: 1, character: 0 }, end: { line: 1, character: 1 } }, severity: 2, message: 'Warning 1', source: 'test' },
        { range: { start: { line: 2, character: 0 }, end: { line: 2, character: 1 } }, severity: 2, message: 'Warning 2', source: 'test' },
      ])
      expect(store.warningCount).toBe(2)
    })

    it('should detect hasErrors correctly', () => {
      const store = useEditorStore()
      expect(store.hasErrors).toBe(false)
      
      store.setDiagnostics([
        { range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, severity: 1, message: 'Error', source: 'test' },
      ])
      expect(store.hasErrors).toBe(true)
    })

    it('should sort diagnostics by severity and line', () => {
      const store = useEditorStore()
      store.setDiagnostics([
        { range: { start: { line: 2, character: 0 }, end: { line: 2, character: 1 } }, severity: 2, message: 'Warning', source: 'test' },
        { range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, severity: 1, message: 'Error', source: 'test' },
        { range: { start: { line: 1, character: 0 }, end: { line: 1, character: 1 } }, severity: 3, message: 'Info', source: 'test' },
      ])
      
      const sorted = store.sortedDiagnostics
      expect(sorted[0].severity).toBe(1) // Error first
      expect(sorted[1].severity).toBe(2) // Warning second
      expect(sorted[2].severity).toBe(3) // Info last
    })
  })

  describe('getDiagnosticsAtLine', () => {
    it('should return diagnostics at specific line', () => {
      const store = useEditorStore()
      store.setDiagnostics([
        { range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, severity: 1, message: 'Error at line 0', source: 'test' },
        { range: { start: { line: 1, character: 0 }, end: { line: 1, character: 1 } }, severity: 2, message: 'Warning at line 1', source: 'test' },
        { range: { start: { line: 0, character: 5 }, end: { line: 0, character: 10 } }, severity: 1, message: 'Another error at line 0', source: 'test' },
      ])
      
      const line0Diagnostics = store.getDiagnosticsAtLine(0)
      expect(line0Diagnostics.length).toBe(2)
    })

    it('should return empty array for line with no diagnostics', () => {
      const store = useEditorStore()
      store.setDiagnostics([
        { range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, severity: 1, message: 'Error', source: 'test' },
      ])
      
      const line5Diagnostics = store.getDiagnosticsAtLine(5)
      expect(line5Diagnostics).toEqual([])
    })
  })

  describe('reset', () => {
    it('should reset all state to initial values', () => {
      const store = useEditorStore()
      
      // Modify state
      store.setContent('SELECT 1')
      store.setDialect('sparksql')
      store.setDiagnostics([
        { range: { start: { line: 0, character: 0 }, end: { line: 0, character: 1 } }, severity: 1, message: 'Error', source: 'test' },
      ])
      store.setCursorPosition(5, 10)
      store.setLinting(true)
      
      // Reset
      store.reset()
      
      // Verify reset
      expect(store.content).toBe('')
      expect(store.dialect).toBe('ansi')
      expect(store.diagnostics).toEqual([])
      expect(store.cursorPosition).toEqual({ line: 1, column: 1 })
      expect(store.isLinting).toBe(false)
    })
  })
})

describe('ConnectionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('should be disconnected initially', () => {
      const store = useConnectionStore()
      expect(store.status).toBe('disconnected')
    })

    it('should have zero reconnect attempts initially', () => {
      const store = useConnectionStore()
      expect(store.reconnectAttempt).toBe(0)
    })
  })

  describe('setStatus', () => {
    it('should update status to connected', () => {
      const store = useConnectionStore()
      store.setStatus('connected')
      expect(store.status).toBe('connected')
    })

    it('should update status to connecting', () => {
      const store = useConnectionStore()
      store.setStatus('connecting')
      expect(store.status).toBe('connecting')
    })

    it('should reset reconnect attempts on connected', () => {
      const store = useConnectionStore()
      store.setReconnectAttempt(5)
      store.setStatus('connected')
      expect(store.reconnectAttempt).toBe(0)
    })

    it('should set lastConnectedAt on connected', () => {
      const store = useConnectionStore()
      store.setStatus('connected')
      expect(store.lastConnectedAt).toBeInstanceOf(Date)
    })

    it('should set lastDisconnectedAt on disconnected', () => {
      const store = useConnectionStore()
      store.setStatus('disconnected')
      expect(store.lastDisconnectedAt).toBeInstanceOf(Date)
    })
  })

  describe('computed properties', () => {
    it('should compute isConnected correctly', () => {
      const store = useConnectionStore()
      expect(store.isConnected).toBe(false)
      
      store.setStatus('connected')
      expect(store.isConnected).toBe(true)
    })

    it('should compute isConnecting correctly', () => {
      const store = useConnectionStore()
      expect(store.isConnecting).toBe(false)
      
      store.setStatus('connecting')
      expect(store.isConnecting).toBe(true)
    })

    it('should compute isDisconnected correctly', () => {
      const store = useConnectionStore()
      expect(store.isDisconnected).toBe(true)
      
      store.setStatus('connected')
      expect(store.isDisconnected).toBe(false)
    })

    it('should compute statusText correctly', () => {
      const store = useConnectionStore()
      
      store.setStatus('connected')
      expect(store.statusText).toBe('Connected')
      
      store.setStatus('disconnected')
      expect(store.statusText).toBe('Disconnected')
      
      store.setReconnectAttempt(3)
      store.setStatus('connecting')
      expect(store.statusText).toContain('Connecting')
      expect(store.statusText).toContain('3')
    })

    it('should compute statusColor correctly', () => {
      const store = useConnectionStore()
      
      store.setStatus('connected')
      expect(store.statusColor).toBe('success')
      
      store.setStatus('connecting')
      expect(store.statusColor).toBe('warning')
      
      store.setStatus('disconnected')
      expect(store.statusColor).toBe('error')
    })
  })

  describe('reset', () => {
    it('should reset all state to initial values', () => {
      const store = useConnectionStore()
      
      // Modify state
      store.setStatus('connected')
      store.setReconnectAttempt(5)
      
      // Reset
      store.reset()
      
      // Verify reset
      expect(store.status).toBe('disconnected')
      expect(store.reconnectAttempt).toBe(0)
      expect(store.lastConnectedAt).toBeNull()
      expect(store.lastDisconnectedAt).toBeNull()
    })
  })
})
