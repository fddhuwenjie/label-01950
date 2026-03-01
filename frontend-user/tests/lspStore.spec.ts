import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, beforeEach } from "vitest";

import { useLspStore } from "../src/store/lsp";

describe("lsp store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("updates status and diagnostics", () => {
    const store = useLspStore();
    store.setStatus("connected");
    store.setDiagnostics([{ message: "err", line: 1, column: 2 }]);
    expect(store.status).toBe("connected");
    expect(store.diagnostics.length).toBe(1);
  });
});
