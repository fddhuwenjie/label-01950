<template>
  <div class="status-bar">
    <div class="status-bar-left">
      <span class="connection-status">
        <span :class="['status-dot', connectionStore.status]"></span>
        <span class="status-text">{{ connectionStore.statusText }}</span>
      </span>
    </div>

    <div class="status-bar-center">
      <span v-if="editorStore.isLinting" class="linting-indicator">
        <a-spin size="small" />
        <span>分析中...</span>
      </span>
      <span v-else class="diagnostics-summary">
        <span v-if="editorStore.errorCount > 0" class="severity-error">
          <ExclamationCircleOutlined /> {{ editorStore.errorCount }} 个错误
        </span>
        <span v-if="editorStore.warningCount > 0" class="severity-warning">
          <WarningOutlined /> {{ editorStore.warningCount }} 个警告
        </span>
        <span v-if="editorStore.infoCount > 0" class="severity-info">
          <InfoCircleOutlined /> {{ editorStore.infoCount }} 个提示
        </span>
        <span v-if="!editorStore.hasErrors && editorStore.warningCount === 0 && editorStore.infoCount === 0" class="no-issues">
          <CheckCircleOutlined /> 无问题
        </span>
      </span>
    </div>

    <div class="status-bar-right">
      <span class="cursor-position">
        行 {{ editorStore.cursorPosition.line }}, 列 {{ editorStore.cursorPosition.column }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ExclamationCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons-vue'
import { useEditorStore } from '@/stores/editor'
import { useConnectionStore } from '@/stores/connection'

const editorStore = useEditorStore()
const connectionStore = useConnectionStore()
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: $status-bar-height;
  padding: 0 $spacing-md;
  background-color: #007acc;
  color: $text-inverse;
  font-size: $font-size-sm;
  user-select: none;
}

.status-bar-left,
.status-bar-center,
.status-bar-right {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;

  &.connected {
    background-color: $success-color;
    box-shadow: 0 0 6px rgba($success-color, 0.8);
  }

  &.connecting {
    background-color: $warning-color;
    animation: pulse 1.5s infinite;
  }

  &.disconnected {
    background-color: $error-color;
  }
}

.linting-indicator {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.diagnostics-summary {
  display: flex;
  align-items: center;
  gap: $spacing-md;

  span {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.severity-error {
  color: #ff6b6b;
}

.severity-warning {
  color: #ffd93d;
}

.severity-info {
  color: #74c0fc;
}

.no-issues {
  color: #69db7c;
}

.cursor-position {
  padding: 0 $spacing-sm;
  border-right: 1px solid rgba(255, 255, 255, 0.3);
}

.dialect-badge {
  padding: 2px $spacing-sm;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: $border-radius-sm;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
