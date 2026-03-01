import { defineStore } from "pinia";
import { ref } from "vue";

import { createCompletion, listCompletions, type CompletionItem } from "../api/completions";

export const useCatalogStore = defineStore("catalog", () => {
  const items = ref<CompletionItem[]>([]);
  const loading = ref(false);

  async function fetchAll(dialect: string, workspaceId: number | null) {
    loading.value = true;
    try {
      items.value = await listCompletions({
        dialect,
        workspace_id: workspaceId ?? undefined,
      });
    } finally {
      loading.value = false;
    }
  }

  async function addTable(payload: { value: string; dialect: string; workspace_id?: number | null }) {
    const created = await createCompletion({
      category: "table",
      value: payload.value,
      dialect: payload.dialect,
      workspace_id: payload.workspace_id,
    });
    items.value.push(created);
    return created;
  }

  return {
    items,
    loading,
    fetchAll,
    addTable,
  };
});
