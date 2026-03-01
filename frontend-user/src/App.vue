<template>
  <a-config-provider
    :theme="{
      token: {
        colorPrimary: '#3B82F6',
        borderRadius: 10
      }
    }"
  >
    <div class="app-shell">
      <header class="app-header">
        <div class="brand">SQL AI Editor</div>
        <ConnectionStatus />
      </header>
      <main class="app-main">
        <EditorView />
      </main>
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import EditorView from "./views/EditorView.vue";
import ConnectionStatus from "./components/ConnectionStatus.vue";
</script>
