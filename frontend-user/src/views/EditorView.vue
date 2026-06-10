<template>
  <div class="editor-view">
    <!-- Header -->
    <header class="editor-header">
      <div class="header-left">
        <h1 class="app-title">
          <CodeOutlined />
          SQL 智能编辑器
        </h1>
      </div>

      <div class="header-center">
      </div>

      <div class="header-right">
        <a-button type="primary" :loading="isAnalyzing" @click="analyzeCode">
          <template #icon><ThunderboltOutlined /></template>
          分析
        </a-button>
        <a-button :type="showExplainPanel ? 'default' : 'default'" :loading="isExplaining" @click="handleExplain">
          <template #icon><LineChartOutlined /></template>
          Explain
        </a-button>
        <a-button @click="formatCode">
          <template #icon><FormatPainterOutlined /></template>
          格式化
        </a-button>
        <a-button @click="clearEditor">
          <template #icon><ClearOutlined /></template>
          清空
        </a-button>
        <DialectSelector v-model="editorStore.dialect" @change="handleDialectChange" />
      </div>
    </header>

    <!-- Main Content -->
    <main class="editor-main">
      <div class="editor-container">
        <SqlEditor
          ref="sqlEditorRef"
          v-model="editorStore.content"
          :request-completion="requestCompletion"
          @change="handleContentChange"
          @cursor-change="handleCursorChange"
        />
      </div>

      <!-- Diagnostics Panel -->
      <transition name="slide-up">
        <div v-if="showDiagnostics" class="diagnostics-container">
          <DiagnosticsPanel @close="showDiagnostics = false" @goto="gotoPosition" />
        </div>
      </transition>

      <!-- Toggle Diagnostics Button -->
      <div v-if="!showDiagnostics" class="toggle-diagnostics" @click="showDiagnostics = true">
        <span class="toggle-text">
          <ExclamationCircleOutlined v-if="editorStore.hasErrors" />
          <WarningOutlined v-else-if="editorStore.warningCount > 0" />
          <CheckCircleOutlined v-else />
          问题 ({{ editorStore.diagnostics.length }})
        </span>
      </div>

      <!-- Execution Plan Panel -->
      <transition name="slide-up">
        <div v-if="showExplainPanel" class="explain-container">
          <ExplainPlan :plan="explainResult" />
          <div class="close-explain-btn" @click="showExplainPanel = false">
            <CloseOutlined />
          </div>
        </div>
      </transition>
    </main>

    <!-- Status Bar -->
    <StatusBar />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  CodeOutlined,
  ThunderboltOutlined,
  FormatPainterOutlined,
  ClearOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  LineChartOutlined,
  CloseOutlined,
} from '@ant-design/icons-vue'

import SqlEditor from '@/components/SqlEditor.vue'
import StatusBar from '@/components/StatusBar.vue'
import DiagnosticsPanel from '@/components/DiagnosticsPanel.vue'
import DialectSelector from '@/components/DialectSelector.vue'
import ExplainPlan from '@/components/ExplainPlan.vue'
import { explainSql, type ExplainResponse } from '@/api/explain'

import { useEditorStore } from '@/stores/editor'
import { useConnectionStore } from '@/stores/connection'
import { createWebSocketClient, type CompletionItem, type Diagnostic } from '@/api/websocket'
import type { SqlDialect } from '@/stores/editor'

const editorStore = useEditorStore()
const connectionStore = useConnectionStore()

const sqlEditorRef = ref<InstanceType<typeof SqlEditor> | null>(null)
const showDiagnostics = ref(true)
const isAnalyzing = ref(false)
const showExplainPanel = ref(false)
const isExplaining = ref(false)
const explainResult = ref<ExplainResponse | null>(null)

// WebSocket client
const wsUrl = import.meta.env.PROD
  ? `ws://${window.location.host}/ws`
  : 'ws://localhost:8000/ws'

const wsClient = createWebSocketClient({
  url: wsUrl,
  onStatusChange: (status) => {
    connectionStore.setStatus(status)
    if (status === 'connected') {
      message.success('已连接到 LSP 服务器')
      // Open document on connect
      if (editorStore.content) {
        wsClient.didOpen(editorStore.documentUri, editorStore.content)
      }
    } else if (status === 'disconnected') {
      message.warning('与 LSP 服务器断开连接')
    }
  },
  onDiagnostics: (_uri: string, diagnostics: Diagnostic[]) => {
    editorStore.setDiagnostics(diagnostics)
    editorStore.setLinting(false)
  },
})

// Handle content changes
async function handleContentChange(content: string) {
  if (!connectionStore.isConnected) return

  editorStore.setLinting(true)
  try {
    await wsClient.didChange(editorStore.documentUri, content)
    // Note: diagnostics are handled in onDiagnostics callback
    // setLinting(false) is called there
  } catch (error) {
    console.error('Failed to send content change:', error)
    editorStore.setLinting(false)
  }
}

// Handle cursor position changes
function handleCursorChange(line: number, column: number) {
  editorStore.setCursorPosition(line, column)
}

// Handle dialect change
async function handleDialectChange(dialect: SqlDialect) {
  if (!connectionStore.isConnected) return

  try {
    await wsClient.setDialect(editorStore.documentUri, dialect)
    const dialectNames: Record<string, string> = { ansi: 'ANSI SQL', sparksql: 'SparkSQL', hive: 'HiveSQL' }
    message.success(`已切换到 ${dialectNames[dialect] || dialect}`)
  } catch (error) {
    console.error('Failed to set dialect:', error)
    message.error('切换方言失败')
  }
}

// Request completion from server
async function requestCompletion(line: number, character: number): Promise<CompletionItem[]> {
  if (!connectionStore.isConnected) return []

  try {
    return await wsClient.requestCompletion(editorStore.documentUri, { line, character })
  } catch (error) {
    console.error('Completion error:', error)
    return []
  }
}

// Analyze code manually
async function analyzeCode() {
  if (!connectionStore.isConnected) {
    message.warning('未连接到 LSP 服务器')
    return
  }

  isAnalyzing.value = true
  editorStore.setLinting(true)

  try {
    await wsClient.didChange(editorStore.documentUri, editorStore.content)
    message.success('分析完成')
  } catch (error) {
    console.error('Analysis failed:', error)
    message.error('分析失败')
  } finally {
    isAnalyzing.value = false
  }
}

// Explain SQL execution plan
async function handleExplain() {
  if (!editorStore.content.trim()) {
    message.warning('请先输入 SQL 语句')
    return
  }

  if (showExplainPanel.value && explainResult.value) {
    showExplainPanel.value = false
    return
  }

  isExplaining.value = true

  try {
    const result = await explainSql(editorStore.content, editorStore.dialect)
    explainResult.value = result
    showExplainPanel.value = true
    message.success('执行计划生成成功')
  } catch (error: any) {
    console.error('Explain failed:', error)
    const errorMsg = error?.response?.data?.error?.message || error.message || '生成执行计划失败'
    message.error(errorMsg)
  } finally {
    isExplaining.value = false
  }
}

// Format code (placeholder - SQLFluff can format but we'd need additional endpoint)
function formatCode() {
  message.info('格式化功能即将推出')
}

// Clear editor
function clearEditor() {
  editorStore.setContent('')
  editorStore.clearDiagnostics()
  sqlEditorRef.value?.setValue('')
  message.success('编辑器已清空')
}

// Go to position in editor
function gotoPosition(line: number, column: number) {
  // Monaco editor position navigation would be implemented here
  console.log(`Go to line ${line}, column ${column}`)
}

// Lifecycle
onMounted(() => {
  wsClient.connect()

  // Set initial sample SQL (correct syntax)
  const sampleSql = `-- SQL 智能编辑器示例
-- 输入 SQL 语句，实时检查语法错误！

SELECT
    id,
    name,
    email,
    status
FROM users
WHERE status = 'active'
ORDER BY name
LIMIT 10;
`
  editorStore.setContent(sampleSql)
})

onUnmounted(() => {
  wsClient.disconnect()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.editor-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: $bg-base;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 $spacing-lg;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.header-left,
.header-center,
.header-right {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.app-title {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.editor-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: $spacing-md;
  min-height: 0;
  gap: $spacing-md;
}

.editor-container {
  flex: 1;
  min-height: 0;
  background-color: $bg-editor;
  border-radius: $border-radius-md;
  box-shadow: $shadow-md;
  overflow: hidden;
}

.diagnostics-container {
  height: $diagnostics-panel-height;
  flex-shrink: 0;
  background-color: $bg-card;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.toggle-diagnostics {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: $spacing-sm $spacing-md;
  background-color: $bg-card;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background-color: darken($bg-card, 3%);
  }

  .toggle-text {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.explain-container {
  height: 340px;
  flex-shrink: 0;
  background-color: $bg-card;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
  position: relative;
}

.close-explain-btn {
  position: absolute;
  top: 10px;
  right: 12px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.8);
  border-radius: 4px;
  transition: all $transition-fast;
  z-index: 10;

  &:hover {
    background: rgba(255, 255, 255, 0.2);
    color: #fff;
  }
}

// Transitions
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(20px);
  opacity: 0;
}
</style>
