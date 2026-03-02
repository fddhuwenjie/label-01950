<template>
  <a-config-provider :theme="themeConfig">
    <div class="app-container">
      <EditorView />
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { theme } from 'ant-design-vue'
import EditorView from './views/EditorView.vue'

const themeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 8,
  },
}
</script>

<style lang="scss">
.app-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #f0f2f5;
}
</style>
