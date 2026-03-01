import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, beforeEach, vi } from "vitest";

const catalogApiMocks = vi.hoisted(() => ({
  listCompletions: vi.fn(),
  createCompletion: vi.fn(),
}));

vi.mock("../src/api/completions", () => catalogApiMocks);

import { useCatalogStore } from "../src/store/catalog";

describe("catalog store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    catalogApiMocks.listCompletions.mockResolvedValue([
      { id: 1, category: "table", value: "t1", dialect: "hive" },
    ]);
    catalogApiMocks.createCompletion.mockResolvedValue({
      id: 2,
      category: "table",
      value: "t2",
      dialect: "hive",
      workspace_id: null,
    });
  });

  it("fetches completions and adds table", async () => {
    const store = useCatalogStore();
    await store.fetchAll("hive", null);
    expect(store.items.length).toBe(1);
    await store.addTable({ value: "t2", dialect: "hive" });
    expect(store.items.length).toBe(2);
  });
});
