<template>
  <div class="sql-editor-container">
    <div ref="editorContainer" class="editor-wrapper"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { registerSqlLanguage, createEditorOptions, getSeverityClass } from '@/utils/monaco-config'
import { createCompletionProvider } from '@/utils/sql-completion'
import { useEditorStore } from '@/stores/editor'
import { debounce } from '@/utils/reconnect'
import type { Diagnostic, CompletionItem } from '@/api/websocket'

const props = defineProps<{
  modelValue: string
  requestCompletion: (line: number, character: number) => Promise<CompletionItem[]>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
  (e: 'cursorChange', line: number, column: number): void
}>()

const editorStore = useEditorStore()
const editorContainer = ref<HTMLElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null
let completionProvider: monaco.IDisposable | null = null

// Debounced change handler
const debouncedChange = debounce((value: string) => {
  emit('change', value)
}, 300)

function initEditor() {
  if (!editorContainer.value) return

  // Register SQL language
  registerSqlLanguage()

  // Create editor
  editor = monaco.editor.create(editorContainer.value, {
    ...createEditorOptions(),
    value: props.modelValue,
  })

  // Register completion provider
  completionProvider = monaco.languages.registerCompletionItemProvider(
    'sql',
    createCompletionProvider(props.requestCompletion)
  )

  // Content change listener
  editor.onDidChangeModelContent(() => {
    const value = editor?.getValue() || ''
    emit('update:modelValue', value)
    debouncedChange(value)
  })

  // Cursor position listener
  editor.onDidChangeCursorPosition((e) => {
    emit('cursorChange', e.position.lineNumber, e.position.column)
    editorStore.setCursorPosition(e.position.lineNumber, e.position.column)
  })
}

function updateMarkers(diagnostics: Diagnostic[]) {
  if (!editor) return

  const model = editor.getModel()
  if (!model) return

  const markers: monaco.editor.IMarkerData[] = diagnostics.map((d) => ({
    severity: getSeverityClass(d.severity),
    message: d.message,
    startLineNumber: d.range.start.line + 1,
    startColumn: d.range.start.character + 1,
    endLineNumber: d.range.end.line + 1,
    endColumn: d.range.end.character + 1,
    source: d.source,
    code: d.code || undefined,
  }))

  monaco.editor.setModelMarkers(model, 'sqlfluff', markers)
}

function setValue(value: string) {
  if (editor && editor.getValue() !== value) {
    editor.setValue(value)
  }
}

function focus() {
  editor?.focus()
}

function getPosition(): { line: number; column: number } | null {
  const position = editor?.getPosition()
  if (position) {
    return { line: position.lineNumber, column: position.column }
  }
  return null
}

// Watch for external value changes
watch(
  () => props.modelValue,
  (newValue) => {
    if (editor && editor.getValue() !== newValue) {
      editor.setValue(newValue)
    }
  }
)

// Watch for diagnostics changes
watch(
  () => editorStore.diagnostics,
  (diagnostics) => {
    updateMarkers(diagnostics)
  },
  { deep: true }
)

onMounted(() => {
  initEditor()
})

onUnmounted(() => {
  completionProvider?.dispose()
  editor?.dispose()
})

defineExpose({
  setValue,
  focus,
  getPosition,
  updateMarkers,
})
</script>

<style lang="scss" scoped>
.sql-editor-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-wrapper {
  flex: 1;
  min-height: 0;
  border-radius: 8px;
  overflow: hidden;
}
</style>
