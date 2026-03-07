import { defineConfig } from "vite";
import vue2 from "@vitejs/plugin-vue2";

export default defineConfig({
  plugins: [vue2()],
  build: {
    lib: {
      entry: "./src/index.js",
      name: "AIChatWidget",
      fileName: "ai-chat",
      formats: ["umd"],
    },
    rollupOptions: {
      // Bundle everything — no external deps for UMD widget
    },
  },
});
