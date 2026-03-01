import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { describe, expect, it, beforeEach } from "vitest";

import ErrorList from "../src/components/ErrorList.vue";
import { useLspStore } from "../src/store/lsp";

describe("ErrorList", () => {
  let pinia = createPinia();

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it("renders diagnostics list", () => {
    const store = useLspStore();
    store.setDiagnostics([{ message: "语法错误", line: 1, column: 2 }]);
    const wrapper = mount(ErrorList, {
      global: {
        plugins: [pinia],
      },
    });
    expect(wrapper.text()).toContain("语法错误");
  });
});
