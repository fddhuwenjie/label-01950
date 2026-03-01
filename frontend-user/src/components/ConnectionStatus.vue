<template>
  <div class="status-chip" :class="statusClass">
    <span class="dot" />
    <span>{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useLspStore } from "../store/lsp";

const store = useLspStore();

const label = computed(() => {
  if (store.status === "connected") return "已连接";
  if (store.status === "connecting") return "连接中";
  return "已断开";
});

const statusClass = computed(() => store.status);
</script>

<style scoped lang="scss">
.status-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  color: #ffffff;
  font-size: 12px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #f97316;
}

.connected .dot {
  background: #22c55e;
}

.connecting .dot {
  background: #f59e0b;
}
</style>
