import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: [
      {
        find: /^vscode\/.*$/,
        replacement: "/src/monaco/vscode-shim.ts",
      },
      {
        find: "vscode",
        replacement: "/src/monaco/vscode-shim.ts",
      },
      {
        find: /^@codingame\/monaco-vscode-.*$/,
        replacement: "/src/monaco/vscode-overrides-shim.ts",
      },
      {
        find: "monaco-editor/esm/vs/platform/product/common/productService",
        replacement: "/src/monaco/productService.ts",
      },
      {
        find: "monaco-editor/esm/vs/platform/product/common/productService.js",
        replacement: "/src/monaco/productService.ts",
      },
      {
        find: "monaco-editor/esm/vs/platform/uriIdentity/common/uriIdentity",
        replacement: "/src/monaco/uriIdentity.ts",
      },
      {
        find: "monaco-editor/esm/vs/platform/uriIdentity/common/uriIdentity.js",
        replacement: "/src/monaco/uriIdentity.ts",
      },
    ],
  },
  server: {
    port: 8081,
  },
  test: {
    environment: "jsdom",
  },
});
