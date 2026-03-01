import { defineStore } from "pinia";
import { ref } from "vue";

import {
  createWorkspace,
  deleteWorkspace,
  listWorkspaces,
  updateWorkspace,
  type Workspace,
} from "../api/workspaces";

export const useWorkspaceStore = defineStore("workspace", () => {
  const items = ref<Workspace[]>([]);
  const loading = ref(false);
  const selectedId = ref<number | null>(null);

  async function fetchAll() {
    loading.value = true;
    try {
      items.value = await listWorkspaces();
      if (items.value.length > 0 && selectedId.value === null) {
        selectedId.value = items.value[0].id;
      }
    } finally {
      loading.value = false;
    }
  }

  async function addWorkspace(payload: { name: string; dialect: string }) {
    const created = await createWorkspace(payload);
    items.value.push(created);
    selectedId.value = created.id;
    return created;
  }

  async function editWorkspace(id: number, payload: { name: string; dialect: string }) {
    const updated = await updateWorkspace(id, payload);
    items.value = items.value.map((item) => (item.id === id ? updated : item));
    return updated;
  }

  async function removeWorkspace(id: number) {
    await deleteWorkspace(id);
    items.value = items.value.filter((item) => item.id !== id);
    if (selectedId.value === id) {
      selectedId.value = items.value[0]?.id ?? null;
    }
  }

  function setSelectedId(id: number | null) {
    selectedId.value = id;
  }

  return {
    items,
    loading,
    selectedId,
    fetchAll,
    addWorkspace,
    editWorkspace,
    removeWorkspace,
    setSelectedId,
  };
});
