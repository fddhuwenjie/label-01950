import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import { describe, expect, it, beforeEach } from "vitest";

import ConnectionStatus from "../src/components/ConnectionStatus.vue";
import { useLspStore } from "../src/store/lsp";

describe("ConnectionStatus", () => {
  let pinia = createPinia();

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it("renders connected label", () => {
    const store = useLspStore();
    store.setStatus("connected");
    const wrapper = mount(ConnectionStatus, {
      global: {
        plugins: [pinia],
      },
    });
    expect(wrapper.text()).toContain("已连接");
  });
});
