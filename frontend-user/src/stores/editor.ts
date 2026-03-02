/**
 * Editor state management using Pinia.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Diagnostic } from '@/api/websocket'

export type SqlDialect = 'ansi' | 'sparksql' | 'hive'

export interface EditorState {
  content: string
  dialect: SqlDialect
  diagnostics: Diagnostic[]
  cursorPosition: { line: number; column: number }
  isLinting: boolean
}

export const useEditorStore = defineStore('editor', () => {
  // State
  const content = ref('')
  const dialect = ref<SqlDialect>('ansi')
  const diagnostics = ref<Diagnostic[]>([])
  const cursorPosition = ref({ line: 1, column: 1 })
  const isLinting = ref(false)
  const documentUri = ref('file:///editor.sql')

  // Getters
  const errorCount = computed(() => 
    diagnostics.value.filter(d => d.severity === 1).length
  )

  const warningCount = computed(() => 
    diagnostics.value.filter(d => d.severity === 2).length
  )

  const infoCount = computed(() => 
    diagnostics.value.filter(d => d.severity === 3 || d.severity === 4).length
  )

  const hasErrors = computed(() => errorCount.value > 0)

  const sortedDiagnostics = computed(() => {
    return [...diagnostics.value].sort((a, b) => {
      // Sort by severity first (errors first)
      if (a.severity !== b.severity) {
        return a.severity - b.severity
      }
      // Then by line number
      return a.range.start.line - b.range.start.line
    })
  })

  // Actions
  function setContent(newContent: string) {
    content.value = newContent
  }

  function setDialect(newDialect: SqlDialect) {
    dialect.value = newDialect
  }

  function setDiagnostics(newDiagnostics: Diagnostic[]) {
    diagnostics.value = newDiagnostics
    isLinting.value = false
  }

  function clearDiagnostics() {
    diagnostics.value = []
  }

  function setCursorPosition(line: number, column: number) {
    cursorPosition.value = { line, column }
  }

  function setLinting(linting: boolean) {
    isLinting.value = linting
  }

  function getDiagnosticsAtLine(line: number): Diagnostic[] {
    return diagnostics.value.filter(d => d.range.start.line === line)
  }

  function reset() {
    content.value = ''
    dialect.value = 'ansi'
    diagnostics.value = []
    cursorPosition.value = { line: 1, column: 1 }
    isLinting.value = false
  }

  return {
    // State
    content,
    dialect,
    diagnostics,
    cursorPosition,
    isLinting,
    documentUri,

    // Getters
    errorCount,
    warningCount,
    infoCount,
    hasErrors,
    sortedDiagnostics,

    // Actions
    setContent,
    setDialect,
    setDiagnostics,
    clearDiagnostics,
    setCursorPosition,
    setLinting,
    getDiagnosticsAtLine,
    reset,
  }
})
