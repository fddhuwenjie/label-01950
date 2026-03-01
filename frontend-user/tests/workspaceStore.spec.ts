import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, beforeEach, vi } from "vitest";

const workspaceApiMocks = vi.hoisted(() => ({
  listWorkspaces: vi.fn(),
  createWorkspace: vi.fn(),
  updateWorkspace: vi.fn(),
  deleteWorkspace: vi.fn(),
}));

vi.mock("../src/api/workspaces", () => workspaceApiMocks);

import { useWorkspaceStore } from "../src/store/workspace";

describe("workspace store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    workspaceApiMocks.listWorkspaces.mockResolvedValue([
      { id: 1, name: "main", dialect: "sparksql" },
    ]);
    workspaceApiMocks.createWorkspace.mockResolvedValue({ id: 2, name: "new", dialect: "hive" });
    workspaceApiMocks.updateWorkspace.mockResolvedValue({ id: 1, name: "main", dialect: "hive" });
    workspaceApiMocks.deleteWorkspace.mockResolvedValue(undefined);
  });

  it("fetches and sets selected workspace", async () => {
    const store = useWorkspaceStore();
    await store.fetchAll();
    expect(store.items.length).toBe(1);
    expect(store.selectedId).toBe(1);
  });

  it("adds, updates, and removes workspace", async () => {
    const store = useWorkspaceStore();
    await store.fetchAll();
    await store.addWorkspace({ name: "new", dialect: "hive" });
    expect(store.items.length).toBe(2);
    await store.editWorkspace(1, { name: "main", dialect: "hive" });
    expect(store.items.find((item) => item.id === 1)?.dialect).toBe("hive");
    await store.removeWorkspace(1);
    expect(store.items.find((item) => item.id === 1)).toBeUndefined();
  });
});
