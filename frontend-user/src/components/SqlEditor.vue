<template>
  <div class="panel-card editor-card">
    <div class="panel-title">SQL 编辑器</div>
    <div ref="containerRef" class="editor-container"></div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as monaco from "monaco-editor";
import { MonacoLanguageClient } from "monaco-languageclient";
import { CloseAction, ErrorAction } from "vscode-languageclient";
import { toSocket, WebSocketMessageReader, WebSocketMessageWriter } from "vscode-ws-jsonrpc";
import { useCatalogStore } from "../store/catalog";
import { useLspStore } from "../store/lsp";

const containerRef = ref<HTMLDivElement | null>(null);
const store = useLspStore();
const catalogStore = useCatalogStore();

let editor: monaco.editor.IStandaloneCodeEditor | null = null;
let languageClient: MonacoLanguageClient | null = null;
let socket: WebSocket | null = null;
let reconnectTimer: number | null = null;

const completionKindMap: Record<string, monaco.languages.CompletionItemKind> = {
  keyword: monaco.languages.CompletionItemKind.Keyword,
  function: monaco.languages.CompletionItemKind.Function,
  table: monaco.languages.CompletionItemKind.Struct,
};

function createLanguageClient(socketInstance: WebSocket) {
  const socketConnection = toSocket(socketInstance);
  const reader = new WebSocketMessageReader(socketConnection);
  const writer = new WebSocketMessageWriter(socketConnection);
  const client = new MonacoLanguageClient({
    name: "SQLFluff Language Client",
    clientOptions: {
      documentSelector: ["sql"],
      initializationOptions: {
        dialect: store.dialect,
      },
      errorHandler: {
        error: () => ErrorAction.Continue,
        closed: () => CloseAction.Restart,
      },
    },
    connectionProvider: {
      get: async () => ({ reader, writer }),
    },
  });

  client.onNotification("textDocument/publishDiagnostics", (payload: any) => {
    const items = (payload?.diagnostics || []).map((item: any) => ({
      message: item.message || "语法错误",
      line: item.range?.start?.line || 0,
      column: item.range?.start?.character || 0,
    }));
    store.setDiagnostics(items);
  });

  reader.onClose(() => {
    store.setStatus("disconnected");
    client.stop();
    scheduleReconnect();
  });

  client.start();
  return client;
}

async function openSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const baseUrl = import.meta.env.VITE_WS_BASE || `${protocol}://localhost:8000`;
  const wsUrl = `${baseUrl}/ws/lsp`;
  store.setStatus("connecting");
  return new Promise<WebSocket>((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => resolve(ws);
    ws.onerror = () => reject(new Error("ws_error"));
  });
}

async function connect() {
  if (socket) {
    socket.close();
  }
  if (languageClient) {
    languageClient.stop();
  }
  try {
    socket = await openSocket();
    store.setStatus("connected");
    languageClient = createLanguageClient(socket);
  } catch {
    store.setStatus("disconnected");
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
  }
  reconnectTimer = window.setTimeout(() => {
    connect();
  }, 1500);
}

onMounted(() => {
  if (!containerRef.value) return;
  monaco.languages.register({ id: "sql" });
  monaco.languages.registerCompletionItemProvider("sql", {
    provideCompletionItems: () => ({
      suggestions: catalogStore.items.map((item) => ({
        label: item.value,
        kind: completionKindMap[item.category] || monaco.languages.CompletionItemKind.Text,
        insertText: item.value,
      })),
    }),
  });
  editor = monaco.editor.create(containerRef.value, {
    value: "SELECT *\nFROM sample_table\nWHERE id = 1;",
    language: "sql",
    theme: "vs-dark",
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
  });
  connect();
});

watch(
  () => store.dialect,
  () => {
    connect();
  }
);

onBeforeUnmount(() => {
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
  }
  if (socket) {
    socket.close();
  }
  if (languageClient) {
    languageClient.stop();
  }
  if (editor) {
    editor.dispose();
  }
});
</script>

<style scoped lang="scss">
.editor-card {
  display: flex;
  flex-direction: column;
  min-height: 520px;
}

.editor-container {
  flex: 1;
  min-height: 480px;
  border-radius: 12px;
  overflow: hidden;
}
</style>
