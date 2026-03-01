import { defineStore } from "pinia";
import { ref } from "vue";

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

export const useLspStore = defineStore("lsp", () => {
  const status = ref<ConnectionStatus>("disconnected");
  const diagnostics = ref<Array<{ message: string; line: number; column: number }>>([]);
  const dialect = ref("sparksql");
  const lastError = ref<string | null>(null);

  function setStatus(value: ConnectionStatus) {
    status.value = value;
  }

  function setDiagnostics(value: Array<{ message: string; line: number; column: number }>) {
    diagnostics.value = value;
  }

  function setDialect(value: string) {
    dialect.value = value;
  }

  function setLastError(value: string | null) {
    lastError.value = value;
  }

  return {
    status,
    diagnostics,
    dialect,
    lastError,
    setStatus,
    setDiagnostics,
    setDialect,
    setLastError,
  };
});
