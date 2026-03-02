<template>
  <div class="diagnostics-panel">
    <div class="panel-header">
      <span class="panel-title">问题</span>
      <span class="panel-count">{{ editorStore.diagnostics.length }}</span>
      <a-button type="text" size="small" @click="$emit('close')">
        <CloseOutlined />
      </a-button>
    </div>

    <div class="panel-content">
      <a-empty v-if="editorStore.diagnostics.length === 0" description="未检测到问题" />

      <div v-else class="diagnostics-list">
        <div
          v-for="(diagnostic, index) in editorStore.sortedDiagnostics"
          :key="index"
          class="diagnostic-item"
          @click="$emit('goto', diagnostic.range.start.line + 1, diagnostic.range.start.character + 1)"
        >
          <span :class="['severity-icon', getSeverityClass(diagnostic.severity)]">
            <ExclamationCircleOutlined v-if="diagnostic.severity === 1" />
            <WarningOutlined v-else-if="diagnostic.severity === 2" />
            <InfoCircleOutlined v-else />
          </span>
          <span class="diagnostic-message">{{ diagnostic.message }}</span>
          <span class="diagnostic-location">
            [Ln {{ diagnostic.range.start.line + 1 }}, Col {{ diagnostic.range.start.character + 1 }}]
          </span>
          <span v-if="diagnostic.code" class="diagnostic-code">{{ diagnostic.code }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  CloseOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons-vue'
import { useEditorStore } from '@/stores/editor'

defineEmits<{
  (e: 'close'): void
  (e: 'goto', line: number, column: number): void
}>()

const editorStore = useEditorStore()

function getSeverityClass(severity: number): string {
  switch (severity) {
    case 1:
      return 'severity-error'
    case 2:
      return 'severity-warning'
    case 3:
      return 'severity-info'
    case 4:
      return 'severity-hint'
    default:
      return 'severity-info'
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.diagnostics-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-card;
  border-top: 1px solid $border-color;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  background-color: $bg-base;
  border-bottom: 1px solid $border-color;
}

.panel-title {
  font-weight: 600;
  color: $text-primary;
}

.panel-count {
  padding: 0 $spacing-sm;
  font-size: $font-size-sm;
  background-color: $primary-color;
  color: $text-inverse;
  border-radius: 10px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-sm;
}

.diagnostics-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.diagnostic-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-radius: $border-radius-sm;
  cursor: pointer;
  transition: background-color $transition-fast;

  &:hover {
    background-color: $bg-base;
  }
}

.severity-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.severity-error {
  color: $error-color;
}

.severity-warning {
  color: $warning-color;
}

.severity-info {
  color: $info-color;
}

.severity-hint {
  color: $text-secondary;
}

.diagnostic-message {
  flex: 1;
  color: $text-primary;
  font-size: $font-size-sm;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diagnostic-location {
  flex-shrink: 0;
  color: $text-secondary;
  font-size: $font-size-sm;
  font-family: $font-family-code;
}

.diagnostic-code {
  flex-shrink: 0;
  padding: 0 $spacing-xs;
  font-size: 11px;
  background-color: $bg-base;
  border-radius: $border-radius-sm;
  color: $text-secondary;
}
</style>
