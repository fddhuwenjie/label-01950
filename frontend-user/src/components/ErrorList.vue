<template>
  <div class="panel-card">
    <div class="panel-title">语法错误</div>
    <a-empty v-if="items.length === 0" description="未检测到语法错误" />
    <div v-else class="error-list">
      <div v-for="item in items" :key="itemKey(item)" class="error-item">
        <div class="error-message">{{ item.message }}</div>
        <div class="error-meta">行 {{ item.line + 1 }} 列 {{ item.column + 1 }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useLspStore } from "../store/lsp";

const store = useLspStore();
const items = computed(() => store.diagnostics);

function itemKey(item: { message: string; line: number; column: number }) {
  return `${item.line}-${item.column}-${item.message}`;
}
</script>

<style scoped lang="scss">
.error-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.error-item {
  padding: 12px;
  border-radius: 12px;
  background: #fff1f2;
  border: 1px solid #fecdd3;
}

.error-message {
  font-weight: 600;
  margin-bottom: 4px;
}

.error-meta {
  font-size: 12px;
  color: #6b7280;
}
</style>
